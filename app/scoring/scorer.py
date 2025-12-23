from dataclasses import dataclass


@dataclass
class AmusementScores:
    smile: float
    laughter: float
    amusement: float


class AmusementScorer:
    """
    Computes Smile, Laughter, and Amusement scores
    from smoothed facial and audio features.
    """

    def __init__(
        self,
        smile_weights=(0.5, 0.5),           # AU12, AU6
        laughter_weights=(0.3, 0.3, 0.2, 0.2),  # AU12, AU6, AU25, Audio
        amusement_weights=(0.6, 0.4)        # Laughter, Smile
    ):
        self.smile_w = smile_weights
        self.laughter_w = laughter_weights
        self.amusement_w = amusement_weights

    def compute(
        self,
        *,
        au25: float,
        au12: float,
        au6: float,
        audio: float
    ) -> AmusementScores:
        smile = (
            self.smile_w[0] * au12 +
            self.smile_w[1] * au6
        )

        laughter = (
            self.laughter_w[0] * au12 +
            self.laughter_w[1] * au6 +
            self.laughter_w[2] * au25 +
            self.laughter_w[3] * audio
        )

        amusement = (
            self.amusement_w[0] * laughter +
            self.amusement_w[1] * smile
        )

        return AmusementScores(
            smile=smile,
            laughter=laughter,
            amusement=amusement
        )
