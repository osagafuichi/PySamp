from pathlib import Path

from pysamp.cuestore import load_cues
from pysamp.downloader import download
from pysamp.engine import Track, load_track

DOWNLOAD_DIR = Path.home() / "PySamp" / "downloads"


def load_source(source: str) -> Track:
    local = Path(source).expanduser()
    if local.is_file():
        track = load_track(local, track_id=f"{local.stem}-{local.stat().st_size}")
    else:
        path, title = download(source, DOWNLOAD_DIR)
        track = load_track(path, title)
    track.cues = load_cues(track.track_id)
    return track
