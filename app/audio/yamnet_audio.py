import time
import threading
import numpy as np
import sounddevice as sd
import tensorflow as tf

YAMNET_PATH = "models/yamnet.tflite"

# Shared state (read-only from main thread)
audio_laughter_score = 0.0


class YamnetAudio:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

        # Load YAMNet
        self.interpreter = tf.lite.Interpreter(model_path=YAMNET_PATH)
        self.interpreter.allocate_tensors()

        self.input_details = self.interpreter.get_input_details()[0]
        self.output_details = self.interpreter.get_output_details()[0]

        self.expected_len = int(self.input_details["shape"][0])
        self.audio_buffer = np.zeros(self.expected_len, dtype=np.float32)

        self.thread = threading.Thread(
            target=self._audio_loop,
            daemon=True
        )

    def start(self):
        self.thread.start()

    def _audio_loop(self):
        global audio_laughter_score

        def callback(indata, frames, time_info, status):
            x = indata[:, 0]

            if frames >= len(self.audio_buffer):
                self.audio_buffer[:] = x[-len(self.audio_buffer):]
                return

            self.audio_buffer = np.roll(self.audio_buffer, -frames)
            self.audio_buffer[-frames:] = x

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback
        ):
            while True:
                self.interpreter.set_tensor(
                    self.input_details["index"],
                    self.audio_buffer
                )
                self.interpreter.invoke()

                scores = self.interpreter.get_tensor(
                    self.output_details["index"]
                )[0]

                # AudioSet: 0=Laughter, 1=Giggle, 2=Chuckle
                laughter_prob = scores[0] + scores[1] + scores[2]
                audio_laughter_score = float(
                    max(0.0, min(laughter_prob, 1.0))
                )

                time.sleep(0.5)
