import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 44100
NUM_ROWS = 4
NUM_BANKS = 2
NUM_SONGS = NUM_ROWS * NUM_BANKS
CUES_PER_PAGE = 9
NUM_PAGES = 2
NUM_CUES = CUES_PER_PAGE * NUM_PAGES
SEEK_SECONDS = 5


class Track:
    def __init__(self, data: np.ndarray, title: str, track_id: str):
        self.data = data
        self.title = title
        self.track_id = track_id
        self.pos = 0
        self.playing = False
        self.volume = 1.0
        self.active_cue: int | None = None
        self.cues: list[int | None] = [None] * NUM_CUES


def load_track(path: Path, title: str | None = None, track_id: str | None = None) -> Track:
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
    return Track(np.ascontiguousarray(data), title or path.stem, track_id or path.stem)


class Mixer:
    def __init__(self):
        self.tracks: list[Track | None] = [None] * NUM_SONGS
        self._lock = threading.Lock()
        self._stream: sd.OutputStream | None = None

    def set_track(self, song: int, track: Track) -> None:
        with self._lock:
            self.tracks[song] = track

    def trigger(self, song: int, cue: int) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is None or cue >= len(track.cues) or track.cues[cue] is None:
                return
            track.pos = track.cues[cue]
            track.active_cue = cue
            track.playing = True

    def set_volume(self, song: int, volume: float) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is not None:
                track.volume = min(max(volume, 0.0), 1.0)

    def toggle_play(self, song: int) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is None:
                return
            if track.playing:
                track.playing = False
                return
            if track.pos >= len(track.data):
                track.pos = 0
            track.playing = True

    def seek(self, song: int, seconds: float) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is not None:
                target = track.pos + int(seconds * SAMPLE_RATE)
                track.pos = min(max(target, 0), len(track.data) - 1)

    def mark_cue(self, song: int) -> int | None:
        with self._lock:
            track = self.tracks[song]
            if track is None:
                return None
            for slot, value in enumerate(track.cues):
                if value is None:
                    track.cues[slot] = track.pos
                    return slot
            return None

    def remove_last_cue(self, song: int) -> bool:
        with self._lock:
            track = self.tracks[song]
            if track is None:
                return False
            for slot in range(NUM_CUES - 1, -1, -1):
                if track.cues[slot] is not None:
                    track.cues[slot] = None
                    if track.active_cue == slot:
                        track.active_cue = None
                    return True
            return False

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
