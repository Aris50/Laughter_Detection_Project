import time

import cv2
import audio.yamnet_audio as yamnet_audio

from audio.yamnet_audio import YamnetAudio
from face.facial_features import FacialFeatureExtractor
from utils.smoothing import EMASmoother
from scoring.scorer import AmusementScorer
from face.face_tracker import FaceTracker
from ui.overlay import ScoreOverlay
from ui.au_debug_overlay import AUDebugOverlay
from logger.text_logger import TextLogger


BASELINE_FRAMES = 60
SMOOTHING_ALPHA = 0.3


def main():
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

    # ---------- Logging ----------
    logger = TextLogger(
        file_path="logs/log.txt",
        interval=0.2
    )
    # ---------- UI ----------
    overlay = ScoreOverlay()
    au_debug = AUDebugOverlay()

    # ---------- Main loop ----------
    while True:
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

        # ---------- Logging ----------
        current_time = time.time()

        logger.try_log(
            timestamp=current_time,
            au25=smoothed_au25,
            au12=smoothed_au12,
            au6=smoothed_au6,
            audio=smoothed_audio,
            smile=scores.smile,
            laughter=scores.laughter,
            amusement=scores.amusement
        )

        # ---------- UI ----------
        overlay.draw(
            frame,
            scores=scores,
            audio_score=smoothed_audio
        )

        cv2.imshow("Amusement Detection (Face + Audio)", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    tracker.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
