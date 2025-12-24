import time
import cv2
import webbrowser
import audio.yamnet_audio as yamnet_audio

from audio.yamnet_audio import YamnetAudio
from face.facial_features import FacialFeatureExtractor
from utils.smoothing import EMASmoother
from scoring.scorer import AmusementScorer
from face.face_tracker import FaceTracker
from ui.overlay import ScoreOverlay
from ui.au_debug_overlay import AUDebugOverlay
from logger.text_logger import TextLogger

# --- New Imports for Playlist & Server ---
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
    # Opens the local server in the default web browser
    webbrowser.open("http://127.0.0.1:5000")

    print("Waiting for participant registration...")
    while not video_state["ready_to_start"]:
        time.sleep(0.5)

    # 4. Registration Complete - Initialize Logger
    print(f"Participant registered: {video_state['participant']['name']}")

    # Update logger initialization
    logger = TextLogger(file_path="logs/log.txt")
    logger.write_header(video_state["participant"])

    # ---------- Audio ----------
    audio = YamnetAudio()
    audio.start()

    # ---------- Video + Face Tracking ----------
    tracker = FaceTracker(
        model_path="models/face_landmarker.task"
    )

    # ---------- Feature extraction ----------
    feature_extractor = FacialFeatureExtractor(
        baseline_frames=BASELINE_FRAMES
    )

    # ---------- Smoothing ----------
    au25_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    au12_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    au6_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)
    audio_smoother = EMASmoother(alpha=SMOOTHING_ALPHA)

    # ---------- Scoring ----------
    scorer = AmusementScorer()

    # ---------- UI (Optional Debug) ----------
    overlay = ScoreOverlay()
    au_debug = AUDebugOverlay()

    # ---------- Main loop ----------
    while True:
        # Check if playlist is finished
        if video_state["finished"]:
            print("Playlist finished. Ending session.")
            break

        frame, landmarks, size = tracker.read()

        if frame is None:
            break

        if landmarks is not None:
            w, h = size
            au25, au12, au6 = feature_extractor.update(
                landmarks, w, h
            )
        else:
            au25 = au12 = au6 = 0.0

        # ---------- Smoothing ----------
        smoothed_au25 = au25_smoother.update(au25)
        smoothed_au12 = au12_smoother.update(au12)
        smoothed_au6 = au6_smoother.update(au6)
        smoothed_audio = audio_smoother.update(
            yamnet_audio.audio_laughter_score
        )

        # Optional: Draw debug overlay (not shown to user, but useful for dev)
        au_debug.draw(
            frame,
            au25=smoothed_au25,
            au12=smoothed_au12,
            au6=smoothed_au6,
            audio=smoothed_audio
        )

        # ---------- Scoring ----------
        scores = scorer.compute(
            au25=smoothed_au25,
            au12=smoothed_au12,
            au6=smoothed_au6,
            audio=smoothed_audio
        )

        # Get the ID of the video currently playing in the browser
        current_video_id = video_state["current_video_id"]
        is_playing = video_state["is_playing"] # Use if you want to pause logging when paused
        video_time = video_state["video_time"]

        if is_playing:
            logger.try_log(
                timestamp=video_time,
                video_id=current_video_id,  # <-- Passed to logger
                au25=smoothed_au25,
                au12=smoothed_au12,
                au6=smoothed_au6,
                audio=smoothed_audio,
                smile=scores.smile,
                laughter=scores.laughter,
                amusement=scores.amusement
            )

        # ---------- UI ----------
        # We generally do NOT show the cv2 window to the user during the experiment,
        # but you might want it for debugging.

        # overlay.draw(frame, scores=scores, audio_score=smoothed_audio)
        # cv2.imshow("Amusement Detection Debug", frame)

        # Use a small sleep to keep the loop from hogging CPU if imshow is off
        # If showing window, use cv2.waitKey(1) instead
        # if cv2.waitKey(1) & 0xFF == 27:
        #    break
        time.sleep(0.01)

    tracker.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()