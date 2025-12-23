from utils.geometry import dist, eye_aperture

# ---------- Landmark indices ----------
UPPER_LIP = 13
LOWER_LIP = 14
LEFT_MOUTH = 61
RIGHT_MOUTH = 291

LEFT_EYE_UPPER = 159
LEFT_EYE_LOWER = 145
LEFT_EYE_LEFT = 33
LEFT_EYE_RIGHT = 133

RIGHT_EYE_UPPER = 386
RIGHT_EYE_LOWER = 374
RIGHT_EYE_LEFT = 362
RIGHT_EYE_RIGHT = 263


class FacialFeatureExtractor:
    """
    Computes AU25 (mouth openness),
    AU12 (lip corner puller),
    AU6  (cheek raiser via eye aperture).
    Handles baseline calibration internally.
    """

    def __init__(self, baseline_frames=60):
        self.baseline_frames = baseline_frames
        self.baseline_counter = 0

        self.baseline_mouth_width = None
        self.baseline_eye_opening = None

    def update(self, landmarks, img_w, img_h):
        """
        Update facial features for the current frame.

        Returns:
            au25, au12, au6
        """
        au25 = au12 = au6 = 0.0

        # ---- Mouth ----
        upper = (landmarks[UPPER_LIP].x * img_w,
                 landmarks[UPPER_LIP].y * img_h)
        lower = (landmarks[LOWER_LIP].x * img_w,
                 landmarks[LOWER_LIP].y * img_h)
        left = (landmarks[LEFT_MOUTH].x * img_w,
                landmarks[LEFT_MOUTH].y * img_h)
        right = (landmarks[RIGHT_MOUTH].x * img_w,
                 landmarks[RIGHT_MOUTH].y * img_h)

        mouth_open = dist(upper, lower)
        mouth_width = dist(left, right)

        # ---- Eyes ----
        le_open = eye_aperture(
            (landmarks[LEFT_EYE_UPPER].x * img_w,
             landmarks[LEFT_EYE_UPPER].y * img_h),
            (landmarks[LEFT_EYE_LOWER].x * img_w,
             landmarks[LEFT_EYE_LOWER].y * img_h),
            (landmarks[LEFT_EYE_LEFT].x * img_w,
             landmarks[LEFT_EYE_LEFT].y * img_h),
            (landmarks[LEFT_EYE_RIGHT].x * img_w,
             landmarks[LEFT_EYE_RIGHT].y * img_h),
        )

        re_open = eye_aperture(
            (landmarks[RIGHT_EYE_UPPER].x * img_w,
             landmarks[RIGHT_EYE_UPPER].y * img_h),
            (landmarks[RIGHT_EYE_LOWER].x * img_w,
             landmarks[RIGHT_EYE_LOWER].y * img_h),
            (landmarks[RIGHT_EYE_LEFT].x * img_w,
             landmarks[RIGHT_EYE_LEFT].y * img_h),
            (landmarks[RIGHT_EYE_RIGHT].x * img_w,
             landmarks[RIGHT_EYE_RIGHT].y * img_h),
        )

        eye_opening = (le_open + re_open) / 2.0

        # ---- Baseline calibration ----
        if self.baseline_counter < self.baseline_frames:
            self.baseline_counter += 1

            self.baseline_mouth_width = (
                mouth_width if self.baseline_mouth_width is None
                else 0.9 * self.baseline_mouth_width + 0.1 * mouth_width
            )

            self.baseline_eye_opening = (
                eye_opening if self.baseline_eye_opening is None
                else 0.9 * self.baseline_eye_opening + 0.1 * eye_opening
            )

        # ---- AU25 ----
        if mouth_width > 1e-6:
            au25 = mouth_open / mouth_width

        # ---- AU12 ----
        if self.baseline_mouth_width and self.baseline_mouth_width > 1e-6:
            au12 = max(
                0.0,
                (mouth_width - self.baseline_mouth_width)
                / self.baseline_mouth_width
            )

        # ---- AU6 ----
        if self.baseline_eye_opening and self.baseline_eye_opening > 1e-6:
            au6 = max(
                0.0,
                (self.baseline_eye_opening - eye_opening)
                / self.baseline_eye_opening
            )

        return au25, au12, au6
