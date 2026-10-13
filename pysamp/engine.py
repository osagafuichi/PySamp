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
NUM_PADS = 30
MAX_VOICES = 32
MAX_LAYERS = 8
CUES_PER_PAGE = 9
NUM_PAGES = 2
NUM_CUES = CUES_PER_PAGE * NUM_PAGES
SEEK_SECONDS = 5
PITCH_MIN = 0.5
PITCH_MAX = 2.0


class Voice:
    __slots__ = ("data", "pos", "group", "key", "loop", "gain", "fade", "fade_left")

    def __init__(self, data, group=0, key=None, loop=None, gain=1.0):
        self.data = data
        self.gain = gain
        self.pos = 0
        self.group = group
        self.key = key
        self.loop = loop
        self.fade = 0
        self.fade_left = 0

    def next_chunk(self, frames: int) -> np.ndarray:
        if self.loop is None:
            chunk = self.data[self.pos : self.pos + frames]
            self.pos += len(chunk)
            return chunk
        start, stop = self.loop
        idx = np.arange(self.pos, self.pos + frames)
        chunk = self.data[np.where(idx >= stop, start + (idx - start) % (stop - start), idx)]
        self.pos = start + (self.pos + frames - start) % (stop - start) if self.pos + frames >= stop else self.pos + frames
        return chunk

    @property
    def finished(self) -> bool:
        if self.fade and self.fade_left <= 0:
            return True
        return self.loop is None and self.pos >= len(self.data)


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
        self.layers: list[float] = []
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
        self._voices: list[Voice] = []
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
                        other.layers.clear()
            track.active_cue = cue
            if layer and track.playing:
                track.layers.append(track.cues[cue])
                del track.layers[:-MAX_LAYERS]
                return
            track.layers.clear()
            track.pos = track.cues[cue]
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
            track.layers.clear()
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
                    track.layers.clear()

    def hit(self, pad: int) -> None:
        from pysamp import drums

        if not 0 <= pad < NUM_PADS:
            return
        data, group = drums.pads()[pad]
        with self._lock:
            if group:
                self._voices[:] = [v for v in self._voices if v.group != group]
            self._voices.append(Voice(data, group))
            del self._voices[:-MAX_VOICES]

    def note_on(self, preset: int, midi: int, velocity: float = 1.0) -> None:
        from pysamp import instruments

        if not 0 <= preset < len(instruments.INSTRUMENTS):
            return
        if midi not in instruments.midi_range(instruments.INSTRUMENTS[preset]):
            return
        data, loop = instruments.note_data(preset, midi)
        with self._lock:
            self._voices.append(Voice(data, key=midi, loop=loop, gain=min(max(velocity, 0.0), 1.0)))
            del self._voices[:-MAX_VOICES]

    def note_off(self, preset: int, midi: int) -> None:
        from pysamp import instruments

        if not 0 <= preset < len(instruments.INSTRUMENTS):
            return
        fade = max(int(instruments.INSTRUMENTS[preset].release * SAMPLE_RATE), 1)
        with self._lock:
            for voice in self._voices:
                if voice.key == midi and not voice.fade:
                    voice.fade = voice.fade_left = fade

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
    def _read(track: Track, pos: float, frames: int) -> tuple[np.ndarray, float]:
        if track.rate == 1.0:
            start = int(pos)
            chunk = track.data[start : start + frames]
            return chunk, start + len(chunk)
        idx = pos + np.arange(frames) * track.rate
        count = int(np.searchsorted(idx, len(track.data) - 1))
        idx = idx[:count]
        low = idx.astype(np.intp)
        frac = (idx - low).astype(np.float32)[:, None]
        chunk = track.data[low] * (1 - frac) + track.data[low + 1] * frac
        return chunk, pos + count * track.rate if count == frames else len(track.data)

    def _callback(self, outdata, frames, time, status) -> None:
        outdata.fill(0)
        with self._lock:
            for track in self.tracks:
                if track is None:
                    continue
                if track.playing:
                    chunk, track.pos = self._read(track, track.pos, frames)
                    outdata[: len(chunk)] += chunk * track.volume
                    if track.pos >= len(track.data):
                        track.playing = False
                alive = []
                for pos in track.layers:
                    chunk, pos = self._read(track, pos, frames)
                    outdata[: len(chunk)] += chunk * track.volume
                    if pos < len(track.data):
                        alive.append(pos)
                track.layers = alive
            for voice in self._voices:
                chunk = voice.next_chunk(frames)
                if voice.gain != 1.0:
                    chunk = chunk * voice.gain
                if voice.fade:
                    ramp = np.arange(voice.fade_left, voice.fade_left - len(chunk), -1) / voice.fade
                    chunk = chunk * np.maximum(ramp, 0)[:, None].astype(np.float32)
                    voice.fade_left -= len(chunk)
                outdata[: len(chunk)] += chunk
            self._voices[:] = [v for v in self._voices if not v.finished]
            np.clip(outdata, -1.0, 1.0, out=outdata)
            if self._recorder is not None:
                self._recorder.push(outdata)
