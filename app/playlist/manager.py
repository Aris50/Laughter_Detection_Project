import random

# Mock Database: ID and Duration (in seconds)
# You can replace this later with a real SQL query
VIDEO_DB = [
    {"id": "wqMQNIlzdGk", "duration": 24},
    {"id": "dGU5_UUalPA", "duration": 95},

]

TARGET_DURATION = 7 * 60  # 420 seconds


def get_random_playlist():
    """
    Selects videos randomly until total duration is ~7 mins.
    Returns a list of video IDs.
    """
    pool = list(VIDEO_DB)
    random.shuffle(pool)

    playlist = []
    current_total = 0

    for video in pool:
        if current_total + video["duration"] <= TARGET_DURATION + 30:
            playlist.append(video["id"])
            current_total += video["duration"]

    return playlist