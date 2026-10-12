import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from pysamp.recorder import Recorder

SAMPLE_RATE = 44100
NUM_ROWS = 4
NUM_BANKS = 2
NUM_SONGS = NUM_ROWS * NUM_BANKS
NUM_PADS = 40
MAX_VOICES = 32
CUES_PER_PAGE = 9
NUM_PAGES = 2
NUM_CUES = CUES_PER_PAGE * NUM_PAGES
SEEK_SECONDS = 5
PITCH_MIN = 0.5
PITCH_MAX = 2.0


class Track:
    def __init__(self, data: np.ndarray, title: str, track_id: str):
        self.data = data
        self.title = title
        self.track_id = track_id
        self.pos: float = 0
        self.playing = False
        self.volume = 1.0
        self.rate = 1.0
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
        self._voices: list[list] = []
        self._lock = threading.Lock()
        self._stream: sd.OutputStream | None = None
        self._recorder: Recorder | None = None

    def start_recording(self, path: Path) -> None:
        self.stop_recording()
        recorder = Recorder(path, SAMPLE_RATE)
        with self._lock:
            self._recorder = recorder

    def stop_recording(self) -> tuple[Path, int] | None:
        with self._lock:
            recorder, self._recorder = self._recorder, None
        if recorder is None:
            return None
        recorder.finish()
        return recorder.path, recorder.frames

    def recorded_frames(self) -> int | None:
        recorder = self._recorder
        return None if recorder is None else recorder.frames

    def set_track(self, song: int, track: Track) -> None:
        with self._lock:
            self.tracks[song] = track

    def trigger(self, song: int, cue: int, layer: bool = False) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is None or cue >= len(track.cues) or track.cues[cue] is None:
                return
            if not layer:
                for other in self.tracks:
                    if other is not None and other is not track:
                        other.playing = False
            track.pos = track.cues[cue]
            track.active_cue = cue
            track.playing = True

    def set_volume(self, song: int, volume: float) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is not None:
                track.volume = min(max(volume, 0.0), 1.0)

    def set_pitch(self, song: int, rate: float) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is not None:
                track.rate = min(max(rate, PITCH_MIN), PITCH_MAX)

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

    def seek_to(self, song: int, fraction: float) -> None:
        with self._lock:
            track = self.tracks[song]
            if track is not None:
                target = int(fraction * len(track.data))
                track.pos = min(max(target, 0), len(track.data) - 1)

    def mark_cue(self, song: int) -> int | None:
        with self._lock:
            track = self.tracks[song]
            if track is None:
                return None
            for slot, value in enumerate(track.cues):
                if value is None:
                    track.cues[slot] = int(track.pos)
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

    def remove_cue(self, song: int, slot: int) -> bool:
        with self._lock:
            track = self.tracks[song]
            if track is None or not 0 <= slot < NUM_CUES or track.cues[slot] is None:
                return False
            kept = sorted(
                ((pos, old) for old, pos in enumerate(track.cues) if pos is not None and old != slot)
            )
            track.cues[:] = [pos for pos, _ in kept] + [None] * (NUM_CUES - len(kept))
            moved = {old: new for new, (_, old) in enumerate(kept)}
            track.active_cue = moved.get(track.active_cue) if track.active_cue != slot else None
            return True

    def stop_all(self) -> None:
        with self._lock:
            for track in self.tracks:
                if track is not None:
                    track.playing = False

    def hit(self, pad: int) -> None:
        from pysamp import drums

        if not 0 <= pad < NUM_PADS:
            return
        data, group = drums.pads()[pad]
        with self._lock:
            if group:
                self._voices[:] = [v for v in self._voices if v[2] != group]
            self._voices.append([data, 0, group])
            del self._voices[:-MAX_VOICES]

    def start(self) -> None:
        from pysamp import drums

        drums.pads()
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=2, dtype="float32", callback=self._callback
        )
        self._stream.start()

    def stop(self) -> None:
        self.stop_recording()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    @staticmethod
    def _resample(track: Track, frames: int) -> np.ndarray:
        idx = track.pos + np.arange(frames) * track.rate
        count = int(np.searchsorted(idx, len(track.data) - 1))
        idx = idx[:count]
        low = idx.astype(np.intp)
        frac = (idx - low).astype(np.float32)[:, None]
        chunk = track.data[low] * (1 - frac) + track.data[low + 1] * frac
        track.pos = track.pos + count * track.rate if count == frames else len(track.data)
        return chunk

    def _callback(self, outdata, frames, time, status) -> None:
        outdata.fill(0)
        with self._lock:
            for track in self.tracks:
                if track is None or not track.playing:
                    continue
                if track.rate == 1.0:
                    start = int(track.pos)
                    chunk = track.data[start : start + frames]
                    track.pos = start + len(chunk)
                else:
                    chunk = self._resample(track, frames)
                outdata[: len(chunk)] += chunk * track.volume
                if track.pos >= len(track.data):
                    track.playing = False
            for voice in self._voices:
                chunk = voice[0][voice[1] : voice[1] + frames]
                outdata[: len(chunk)] += chunk
                voice[1] += len(chunk)
            self._voices[:] = [v for v in self._voices if v[1] < len(v[0])]
            np.clip(outdata, -1.0, 1.0, out=outdata)
            if self._recorder is not None:
                self._recorder.push(outdata)
