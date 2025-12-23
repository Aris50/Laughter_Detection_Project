import time
import cv2
import numpy as np
import mediapipe as mp
import sounddevice as sd
import threading
import tensorflow as tf

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from utils.geometry import dist, eye_aperture



# ---------- Landmark indices ----------
# Mouth
UPPER_LIP = 13
LOWER_LIP = 14
LEFT_MOUTH = 61
RIGHT_MOUTH = 291

# Eyes
LEFT_EYE_UPPER = 159
LEFT_EYE_LOWER = 145
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133

RIGHT_EYE_UPPER = 386
RIGHT_EYE_LOWER = 374
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263


# ---------- Constants ----------
ALPHA = 0.3
BASELINE_FRAMES = 60  # ~2 seconds
YAMNET_PATH = "models/yamnet.tflite"


# ---------- YAMNet setup ----------
yamnet_interpreter = tf.lite.Interpreter(model_path=YAMNET_PATH)
yamnet_interpreter.allocate_tensors()

yamnet_input = yamnet_interpreter.get_input_details()[0]
yamnet_output = yamnet_interpreter.get_output_details()[0]

audio_laughter_score = 0.0


def yamnet_audio_loop():
    """Continuously updates audio_laughter_score using YAMNet."""
    global audio_laughter_score

    sample_rate = 16000
    expected_len = int(yamnet_input["shape"][0])
    audio_buffer = np.zeros(expected_len, dtype=np.float32)

    def callback(indata, frames, time_info, status):
        nonlocal audio_buffer
        x = indata[:, 0]

        if frames >= len(audio_buffer):
            audio_buffer[:] = x[-len(audio_buffer):]
            return

        audio_buffer = np.roll(audio_buffer, -frames)
        audio_buffer[-frames:] = x

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        callback=callback
    ):
        while True:
            yamnet_interpreter.set_tensor(
                yamnet_input["index"],
                audio_buffer
            )
            yamnet_interpreter.invoke()

            scores = yamnet_interpreter.get_tensor(
                yamnet_output["index"]
            )[0]

            # AudioSet indices:
            # 0 = Laughter, 1 = Giggle, 2 = Chuckle
            laughter_prob = scores[0] + scores[1] + scores[2]
            audio_laughter_score = float(
                max(0.0, min(laughter_prob, 1.0))
            )

            time.sleep(0.5)


# ---------- Main ----------
def main():
    global audio_laughter_score

    # Start audio thread
    threading.Thread(target=yamnet_audio_loop, daemon=True).start()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam")

    face_options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(
            model_asset_path="models/face_landmarker.task"
        ),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1
    )
    landmarker = vision.FaceLandmarker.create_from_options(face_options)

    baseline_mouth_width = None
    baseline_eye_opening = None
    baseline_counter = 0

    smoothed_au25 = smoothed_au12 = smoothed_au6 = 0.0
    smoothed_audio = 0.0

    start = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - start) * 1000)

        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        au25 = au12 = au6 = 0.0

        if result.face_landmarks:
            lm = result.face_landmarks[0]

            # Mouth
            upper = (lm[UPPER_LIP].x * w, lm[UPPER_LIP].y * h)
            lower = (lm[LOWER_LIP].x * w, lm[LOWER_LIP].y * h)
            left = (lm[LEFT_MOUTH].x * w, lm[LEFT_MOUTH].y * h)
            right = (lm[RIGHT_MOUTH].x * w, lm[RIGHT_MOUTH].y * h)

            mouth_open = dist(upper, lower)
            mouth_width = dist(left, right)

            # Eyes
            le_open = eye_aperture(
                (lm[LEFT_EYE_UPPER].x * w, lm[LEFT_EYE_UPPER].y * h),
                (lm[LEFT_EYE_LOWER].x * w, lm[LEFT_EYE_LOWER].y * h),
                (lm[LEFT_EYE_LEFT].x * w, lm[LEFT_EYE_LEFT].y * h),
                (lm[LEFT_EYE_RIGHT].x * w, lm[LEFT_EYE_RIGHT].y * h),
            )
            re_open = eye_aperture(
                (lm[RIGHT_EYE_UPPER].x * w, lm[RIGHT_EYE_UPPER].y * h),
                (lm[RIGHT_EYE_LOWER].x * w, lm[RIGHT_EYE_LOWER].y * h),
                (lm[RIGHT_EYE_LEFT].x * w, lm[RIGHT_EYE_LEFT].y * h),
                (lm[RIGHT_EYE_RIGHT].x * w, lm[RIGHT_EYE_RIGHT].y * h),
            )
            eye_opening = (le_open + re_open) / 2.0

            # Baseline
            if baseline_counter < BASELINE_FRAMES:
                baseline_counter += 1
                baseline_mouth_width = mouth_width if baseline_mouth_width is None \
                    else 0.9 * baseline_mouth_width + 0.1 * mouth_width
                baseline_eye_opening = eye_opening if baseline_eye_opening is None \
                    else 0.9 * baseline_eye_opening + 0.1 * eye_opening

            if mouth_width > 1e-6:
                au25 = mouth_open / mouth_width

            if baseline_mouth_width and baseline_mouth_width > 1e-6:
                au12 = max(0.0, (mouth_width - baseline_mouth_width) / baseline_mouth_width)

            if baseline_eye_opening and baseline_eye_opening > 1e-6:
                au6 = max(0.0, (baseline_eye_opening - eye_opening) / baseline_eye_opening)

        # EMA smoothing
        smoothed_au25 = ALPHA * au25 + (1 - ALPHA) * smoothed_au25
        smoothed_au12 = ALPHA * au12 + (1 - ALPHA) * smoothed_au12
        smoothed_au6 = ALPHA * au6 + (1 - ALPHA) * smoothed_au6
        smoothed_audio = ALPHA * audio_laughter_score + (1 - ALPHA) * smoothed_audio

        # Scores
        smile_score = 0.5 * smoothed_au12 + 0.5 * smoothed_au6
        laughter_score = (
            0.3 * smoothed_au12 +
            0.3 * smoothed_au6 +
            0.2 * smoothed_au25 +
            0.2 * smoothed_audio
        )
        amusement_score = 0.6 * laughter_score + 0.4 * smile_score

        # Display
        cv2.putText(frame, f"SmileScore: {smile_score:.3f}", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 100), 2)
        cv2.putText(frame, f"LaughterScore: {laughter_score:.3f}", (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 150, 0), 2)
        cv2.putText(frame, f"Audio Laughter: {smoothed_audio:.3f}", (30, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (100, 255, 255), 2)
        cv2.putText(frame, f"AmusementScore: {amusement_score:.3f}", (30, 145),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Amusement Detection (Face + YAMNet Audio)", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
