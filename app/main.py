import time
import cv2
import webbrowser
import audio.yamnet_audio as yamnet_audio

from persistence.repo import (
    get_or_create_subject,
    create_experiment,
    save_video_score,
    finalize_experiment,
    video_exists
)

from audio.yamnet_audio import YamnetAudio
from face.facial_features import FacialFeatureExtractor
from utils.smoothing import EMASmoother
from scoring.scorer import AmusementScorer
from face.face_tracker import FaceTracker
from ui.overlay import ScoreOverlay
from ui.au_debug_overlay import AUDebugOverlay
from logger.text_logger import TextLogger

from playlist.manager import get_random_playlist
from web.server import start_background_server, set_playlist

BASELINE_FRAMES = 60
SMOOTHING_ALPHA = 0.3


def main():
    # ---------- 1. Prepare Content (Playlist) ----------
    print("Generating playlist...")
    playlist_ids = get_random_playlist()
    set_playlist(playlist_ids)

    # ---------- 2. Start Web Server (Background) ----------
    print("Starting server...")
    video_state = start_background_server()

    # ---------- 3. Launch Browser for the User ----------
    webbrowser.open("http://127.0.0.1:5000")

    print("Waiting for participant registration...")
    while not video_state["ready_to_start"]:
        time.sleep(0.5)

    # ---------- 4. Registration Complete ----------
    participant = video_state["participant"]
    print(f"Participant registered: {participant['name']}")

    # ---------- Create Subject + Experiment in DB ----------
    name = participant.get("name") or "Unknown"
    age_raw = participant.get("age")
    gender = participant.get("gender")

    age = int(age_raw) if age_raw and str(age_raw).isdigit() else None

    exp_type = "single"  # or "group" (later: add to form)

    sid = get_or_create_subject(name=name, age=age, gender=gender)
    eid = create_experiment(sid=sid, exp_type=exp_type)
    print(f"DB: sid={sid}, eid={eid}")

    # ---------- Logger ----------
    logger = TextLogger(file_path="logs/log.txt")
    logger.write_header(participant)

    # ---------- Audio ----------
    audio = YamnetAudio()
    audio.start()

    # ---------- Video + Face Tracking ----------
    tracker = FaceTracker(model_path="models/face_landmarker.task")

    # ---------- Feature extraction ----------
    feature_extractor = FacialFeatureExtractor(baseline_frames=BASELINE_FRAMES)

    # ---------- Smoothing ----------
    au25_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    au12_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    au6_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    audio_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)

    # ---------- Scoring ----------
    scorer = AmusementScorer()

    # ---------- UI (Debug) ----------
    overlay = ScoreOverlay()
    au_debug = AUDebugOverlay()

    # ---------- DB aggregation state ----------
    last_video_id = None
    video_samples = []
    all_samples = []
    saved_video_ids = set()

    # ---------- Main loop ----------
    try:
        while True:
            if video_state["finished"]:
                print("Playlist finished. Ending session.")
                break

            frame, landmarks, size = tracker.read()
            if frame is None:
                break

            if landmarks is not None:
                w, h = size
                au25, au12, au6 = feature_extractor.update(landmarks, w, h)
            else:
                au25 = au12 = au6 = 0.0

            smoothed_au25 = au25_smoother.update(au25)
            smoothed_au12 = au12_smoother.update(au12)
            smoothed_au6 = au6_smoother.update(au6)
            smoothed_audio = audio_smoother.update(yamnet_audio.audio_laughter_score)

            au_debug.draw(
                frame,
                au25=smoothed_au25,
                au12=smoothed_au12,
                au6=smoothed_au6,
                audio=smoothed_audio
            )

            scores = scorer.compute(
                au25=smoothed_au25,
                au12=smoothed_au12,
                au6=smoothed_au6,
                audio=smoothed_audio
            )

            current_video_id = video_state["current_video_id"]
            is_playing = video_state["is_playing"]
            video_time = video_state["video_time"]

            if is_playing:
                logger.try_log(
                    timestamp=video_time,
                    video_id=current_video_id,
                    au25=smoothed_au25,
                    au12=smoothed_au12,
                    au6=smoothed_au6,
                    audio=smoothed_audio,
                    smile=scores.smile,
                    laughter=scores.laughter,
                    amusement=scores.amusement
                )

                all_samples.append(scores.amusement)

                if current_video_id and current_video_id not in ("WAITING", "UNKNOWN"):
                    if video_exists(current_video_id):
                        if last_video_id is None:
                            last_video_id = current_video_id

                        if current_video_id != last_video_id:
                            if video_samples and (last_video_id not in saved_video_ids):
                                mean_score = sum(video_samples) / len(video_samples)
                                save_video_score(eid=eid, vid=last_video_id, score=mean_score)
                                saved_video_ids.add(last_video_id)

                            last_video_id = current_video_id
                            video_samples = []

                        video_samples.append(scores.amusement)

            # Debug UI window (optional)
            overlay.draw(frame, scores=scores, audio_score=smoothed_audio)
            cv2.imshow("Amusement Detection Debug", frame)

            if cv2.waitKey(1) & 0xFF == 27:
                break

            time.sleep(0.01)

    finally:
        # ---------- Finalize DB writes ----------
        if last_video_id and video_samples and (last_video_id not in saved_video_ids):
            mean_score = sum(video_samples) / len(video_samples)
            save_video_score(eid=eid, vid=last_video_id, score=mean_score)
            saved_video_ids.add(last_video_id)

        total_score = (sum(all_samples) / len(all_samples)) if all_samples else 0.0
        finalize_experiment(eid=eid, total_score=total_score)
        print(f"DB: finalized experiment {eid} total_score={total_score:.4f}")

        tracker.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()