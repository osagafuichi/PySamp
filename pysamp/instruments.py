import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from pysamp.engine import SAMPLE_RATE

SAMPLES_DIR = Path(__file__).parent / "samples"
SCALE = (0, 2, 4, 5, 7, 9, 11, 12, 14, 16)
NUM_KEYS = 3 * len(SCALE)
SAMPLE_STEP = 3
PEAK = 0.4
END_FADE = 0.02
LOOP_START = 1.2
LOOP_BLEND = 0.08
CACHE_SIZE = 3
NAMES = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")


@dataclass(frozen=True)
class Instrument:
    id: str
    label: str
    base: int
    release: float
    loop: bool = False


INSTRUMENTS = (
    Instrument("piano", "Grand Piano", 48, 0.4),
    Instrument("epiano", "Electric Piano", 48, 0.3),
    Instrument("organ", "Organ", 48, 0.08, loop=True),
    Instrument("strings", "Strings", 48, 0.5, loop=True),
    Instrument("guitar", "Guitar", 48, 0.25),
    Instrument("bass", "Bass", 36, 0.15),
    Instrument("choir", "Choir", 48, 0.5, loop=True),
    Instrument("lead", "Synth Lead", 48, 0.1, loop=True),
    Instrument("brass", "Brass", 48, 0.15, loop=True),
)


def note_name(midi: int) -> str:
    return f"{NAMES[midi % 12]}{midi // 12 - 1}"


def midi_for_key(instrument: Instrument, key: int) -> int:
    row, col = divmod(key, len(SCALE))
    return instrument.base + 12 * row + SCALE[col]


def key_names(instrument: Instrument) -> list[str]:
    return [note_name(midi_for_key(instrument, key)) for key in range(NUM_KEYS)]


def sample_notes(instrument: Instrument) -> range:
    return range(instrument.base - SAMPLE_STEP, instrument.base + 43, SAMPLE_STEP)


def read_sample(path: Path) -> np.ndarray:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SAMPLE_RATE:
        mono = np.interp(np.arange(int(len(mono) * SAMPLE_RATE / rate)) * rate / SAMPLE_RATE, np.arange(len(mono)), mono)
    return mono.astype(np.float32)


Note = tuple[np.ndarray, tuple[int, int] | None]


def shifted(sample: np.ndarray, semitones: int, loop: bool) -> Note:
    ratio = 2 ** (semitones / 12)
    positions = np.arange(int((len(sample) - 1) / ratio)) * ratio
    out = np.interp(positions, np.arange(len(sample)), sample)
    peak = np.abs(out).max()
    out = out / peak * PEAK if peak else out
    if loop:
        start, stop, blend = int(LOOP_START * SAMPLE_RATE), len(out), int(LOOP_BLEND * SAMPLE_RATE)
        ramp = np.linspace(0, 1, blend)
        out[stop - blend :] = out[stop - blend :] * (1 - ramp) + out[start - blend : start] * ramp
        return out.astype(np.float32)[:, None], (start, stop)
    fade = int(END_FADE * SAMPLE_RATE)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out.astype(np.float32)[:, None], None


_cache: OrderedDict[str, dict[int, Note]] = OrderedDict()
_lock = threading.Lock()


def notes(index: int) -> dict[int, Note]:
    with _lock:
        return _notes(index)


def _notes(index: int) -> dict[int, Note]:
    instrument = INSTRUMENTS[index]
    if instrument.id in _cache:
        _cache.move_to_end(instrument.id)
        return _cache[instrument.id]
    folder = SAMPLES_DIR / instrument.id
    samples = {midi: read_sample(folder / f"{note_name(midi)}.ogg") for midi in sample_notes(instrument)}
    rendered = {}
    for key in range(NUM_KEYS):
        midi = midi_for_key(instrument, key)
        if midi not in rendered:
            nearest = min(samples, key=lambda m: abs(m - midi))
            rendered[midi] = shifted(samples[nearest], midi - nearest, instrument.loop)
    _cache[instrument.id] = rendered
    while len(_cache) > CACHE_SIZE:
        _cache.popitem(last=False)
    return rendered


def note_data(index: int, key: int) -> Note:
    return notes(index)[midi_for_key(INSTRUMENTS[index], key)]
