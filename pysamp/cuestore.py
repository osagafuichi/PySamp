import json
import re
from pathlib import Path

from pysamp.engine import NUM_CUES

CUE_DIR = Path.home() / "PySamp" / "cues"


def _path(track_id: str, cue_dir: Path) -> Path:
    return cue_dir / (re.sub(r"[^A-Za-z0-9_.-]", "_", track_id) + ".json")


def load_cues(track_id: str, cue_dir: Path = CUE_DIR) -> list[int | None]:
    cues: list[int | None] = [None] * NUM_CUES
    try:
        saved = json.loads(_path(track_id, cue_dir).read_text())
    except (OSError, ValueError):
        return cues
    if isinstance(saved, list):
        for slot, value in enumerate(saved[:NUM_CUES]):
            if isinstance(value, int) and value >= 0:
                cues[slot] = value
    return cues


def save_cues(track_id: str, cues: list[int | None], cue_dir: Path = CUE_DIR) -> None:
    cue_dir.mkdir(parents=True, exist_ok=True)
    _path(track_id, cue_dir).write_text(json.dumps(cues))
