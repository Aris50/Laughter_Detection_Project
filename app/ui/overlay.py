import cv2


class ScoreOverlay:
    def draw(self, frame, scores, audio_score):
        cv2.putText(frame, f"SmileScore: {scores.smile:.3f}",
                    (30, 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (0, 255, 100), 2)

        cv2.putText(frame, f"LaughterScore: {scores.laughter:.3f}",
                    (30, 75), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 150, 0), 2)

        cv2.putText(frame, f"Audio Laughter: {audio_score:.3f}",
                    (30, 110), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (100, 255, 255), 2)

        cv2.putText(frame, f"AmusementScore: {scores.amusement:.3f}",
                    (30, 145), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 2)
