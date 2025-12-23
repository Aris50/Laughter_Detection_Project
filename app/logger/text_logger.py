import time
from datetime import datetime
from pathlib import Path


class TextLogger:
    def __init__(self, file_path: str, interval: float = 0.2):
        self.file_path = Path(file_path)
        self.interval = interval
        self.last_log_time = 0.0

        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.file_path, "w") as f:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("# Amusement Detection Log\n")
            f.write(f"# Session start: {now}\n")
            f.write("# time, video_id, au25, au12, au6, audio, smile, laughter, amusement\n")

    def try_log(
        self,
        timestamp,
        video_id,
        au25,
        au12,
        au6,
        audio,
        smile,
        laughter,
        amusement
    ):
        if timestamp - self.last_log_time < self.interval:
            return

        self.last_log_time = timestamp

        time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-4]

        line = (
            f"{time_str}, "
            f"{video_id}, "
            f"{au25:.3f}, "
            f"{au12:.3f}, "
            f"{au6:.3f}, "
            f"{audio:.3f}, "
            f"{smile:.3f}, "
            f"{laughter:.3f}, "
            f"{amusement:.3f}\n"
        )

        with open(self.file_path, "a") as f:
            f.write(line)
