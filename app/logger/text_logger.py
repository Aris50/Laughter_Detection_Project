import time
from datetime import datetime
from pathlib import Path

class TextLogger:
    # We remove the immediate file creation from __init__
    # because we don't have the user-name yet when we create the class
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.header_written = False

    def write_header(self, participant_info):
        """Writes the participant info and column headers."""
        with open(self.file_path, "w") as f:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write("# Amusement Detection Log\n")
            f.write(f"# Date: {now}\n")
            f.write(f"# Subject: {participant_info['name']}\n")
            f.write(f"# Age: {participant_info['age']}\n")
            f.write(f"# Gender: {participant_info['gender']}\n")
            f.write("-" * 30 + "\n")
            f.write("time, video_id, au25, au12, au6, audio, smile, laughter, amusement\n")
        self.header_written = True

    def try_log(self, timestamp, video_id, au25, au12, au6, audio, smile, laughter, amusement):
        if not self.header_written:
            print("Warning: Log header not written yet. Skipping line.")
            return

        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"

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