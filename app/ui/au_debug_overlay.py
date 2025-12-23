import cv2


class AUDebugOverlay:
    """
    Renders AU and audio debug bars on the frame.
    """

    def __init__(
        self,
        origin=(30, 200),
        bar_width=200,
        bar_height=18,
        spacing=28
    ):
        self.x, self.y = origin
        self.bar_width = bar_width
        self.bar_height = bar_height
        self.spacing = spacing

    def _draw_bar(self, frame, label, value, y_offset, color):
        # Clamp value to [0, 1]
        value = max(0.0, min(value, 1.0))

        # Background bar
        cv2.rectangle(
            frame,
            (self.x, y_offset),
            (self.x + self.bar_width, y_offset + self.bar_height),
            (60, 60, 60),
            -1
        )

        # Filled bar
        filled_width = int(self.bar_width * value)
        cv2.rectangle(
            frame,
            (self.x, y_offset),
            (self.x + filled_width, y_offset + self.bar_height),
            color,
            -1
        )

        # Border
        cv2.rectangle(
            frame,
            (self.x, y_offset),
            (self.x + self.bar_width, y_offset + self.bar_height),
            (200, 200, 200),
            1
        )

        # Label
        cv2.putText(
            frame,
            f"{label}: {value:.2f}",
            (self.x + self.bar_width + 10, y_offset + self.bar_height - 3),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1
        )

    def draw(
        self,
        frame,
        *,
        au25,
        au12,
        au6,
        audio
    ):
        y = self.y

        self._draw_bar(frame, "AU25 (Mouth Open)", au25, y, (0, 200, 255))
        y += self.spacing

        self._draw_bar(frame, "AU12 (Smile)", au12, y, (0, 255, 100))
        y += self.spacing

        self._draw_bar(frame, "AU6 (Cheeks)", au6, y, (255, 150, 255))
        y += self.spacing

        self._draw_bar(frame, "Audio Laugh", audio, y, (255, 200, 0))
