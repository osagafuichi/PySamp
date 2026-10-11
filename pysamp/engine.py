import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 44100
NUM_ROWS = 4
NUM_CUES = 10


class Track:
    def __init__(self, data: np.ndarray, title: str):
        self.data = data
        self.title = title
        self.pos = 0
        self.playing = False
        self.volume = 1.0
        self.active_cue: int | None = None
        step = len(data) // NUM_CUES
        self.cues = [i * step for i in range(NUM_CUES)]


def load_track(path: Path) -> Track:
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    if sr != SAMPLE_RATE:
        n_out = int(len(data) * SAMPLE_RATE / sr)
        x_old = np.linspace(0, 1, len(data), endpoint=False)
        x_new = np.linspace(0, 1, n_out, endpoint=False)
        data = np.stack([np.interp(x_new, x_old, data[:, c]) for c in range(2)], axis=1).astype(np.float32)
    return Track(np.ascontiguousarray(data), path.stem)


class Mixer:
    def __init__(self):
        self.tracks: list[Track | None] = [None] * NUM_ROWS
        self._lock = threading.Lock()
        self._stream: sd.OutputStream | None = None

    def set_track(self, row: int, track: Track) -> None:
        with self._lock:
            self.tracks[row] = track

    def trigger(self, row: int, cue: int) -> None:
        with self._lock:
            track = self.tracks[row]
            if track is None or cue >= len(track.cues):
                return
            track.pos = track.cues[cue]
            track.active_cue = cue
            track.playing = True

    def set_volume(self, row: int, volume: float) -> None:
        with self._lock:
            track = self.tracks[row]
            if track is not None:
                track.volume = min(max(volume, 0.0), 1.0)

    def stop_all(self) -> None:
        with self._lock:
            for track in self.tracks:
                if track is not None:
                    track.playing = False

    def start(self) -> None:
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=2, dtype="float32", callback=self._callback
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, outdata, frames, time, status) -> None:
        outdata.fill(0)
        with self._lock:
            for track in self.tracks:
                if track is None or not track.playing:
                    continue
                chunk = track.data[track.pos : track.pos + frames]
                outdata[: len(chunk)] += chunk * track.volume
                track.pos += len(chunk)
                if track.pos >= len(track.data):
                    track.playing = False
        np.clip(outdata, -1.0, 1.0, out=outdata)
