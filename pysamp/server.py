import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from pysamp import instruments
from pysamp.cuestore import save_cues
from pysamp.drums import NAMES
from pysamp.engine import NUM_CUES, NUM_PADS, NUM_SONGS, SAMPLE_RATE, Mixer
from pysamp.loader import load_source

WEB_DIR = Path(__file__).parent / "web"
RECORD_DIR = Path.home() / "PySamp" / "recordings"
PEAK_BINS = 1000
EVENT_INTERVAL = 0.033


def fmt_time(samples: int) -> str:
    seconds = samples // SAMPLE_RATE
    return f"{seconds // 60}:{seconds % 60:02d}"


class SamplerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, mixer: Mixer, port: int = 0):
        super().__init__(("127.0.0.1", port), Handler)
        self.mixer = mixer
        self.token = secrets.token_urlsafe(16)
        self.status = "Select a song, press space to play, m to mark cues."
        self.quit_event = threading.Event()
        self.peak_cache: dict[str, dict] = {}

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/?t={self.token}"

    def state(self) -> dict:
        songs = []
        for track in self.mixer.tracks:
            if track is None:
                songs.append({"loaded": False})
                continue
            songs.append(
                {
                    "loaded": True,
                    "id": track.track_id,
                    "title": track.title,
                    "pos": track.pos,
                    "total": len(track.data),
                    "playing": track.playing,
                    "volume": track.volume,
                    "pitch": track.rate,
                    "active_cue": track.active_cue,
                    "cues": list(track.cues),
                }
            )
        frames = self.mixer.recorded_frames()
        return {
            "rate": SAMPLE_RATE,
            "status": self.status,
            "songs": songs,
            "drum_names": NAMES,
            "presets": [{"label": i.label, "notes": instruments.key_names(i)} for i in instruments.INSTRUMENTS],
            "recording": None if frames is None else frames / SAMPLE_RATE,
        }

    def peaks(self, song: int) -> dict | None:
        track = self.mixer.tracks[song]
        if track is None:
            return None
        if track.track_id not in self.peak_cache:
            mono = track.data.mean(axis=1, dtype=np.float64)
            bins = max(min(PEAK_BINS, len(mono)), 1)
            blocks = mono[: len(mono) // bins * bins].reshape(bins, -1)
            self.peak_cache[track.track_id] = {
                "min": np.round(blocks.min(axis=1), 3).tolist(),
                "max": np.round(blocks.max(axis=1), 3).tolist(),
            }
        return self.peak_cache[track.track_id]

    def command(self, cmd: dict) -> None:
        action = cmd["action"]
        if action == "stop_all":
            self.mixer.stop_all()
            return
        if action == "quit":
            self.quit_event.set()
            return
        if action == "record":
            on = cmd["on"]
            if not isinstance(on, bool):
                raise ValueError("bad on")
            self.record(on)
            return
        if action == "drum":
            pad = cmd["pad"]
            if not isinstance(pad, int) or not 0 <= pad < NUM_PADS:
                raise ValueError("bad pad")
            self.mixer.hit(pad)
            return
        if action in ("note", "preset"):
            preset = cmd["preset"]
            if not isinstance(preset, int) or not 0 <= preset < len(instruments.INSTRUMENTS):
                raise ValueError("bad preset")
            if action == "preset":
                instruments.notes(preset)
                return
            key, on = cmd["key"], cmd["on"]
            if not isinstance(key, int) or not 0 <= key < instruments.NUM_KEYS:
                raise ValueError("bad key")
            if not isinstance(on, bool):
                raise ValueError("bad on")
            if on:
                self.mixer.note_on(preset, key)
            else:
                self.mixer.note_off(preset, key)
            return
        song = cmd["song"]
        if not isinstance(song, int) or not 0 <= song < NUM_SONGS:
            raise ValueError("bad song")
        mixer = self.mixer
        if action == "trigger":
            layer = cmd.get("layer", False)
            if not isinstance(layer, bool):
                raise ValueError("bad layer")
            mixer.trigger(song, int(cmd["cue"]), layer)
        elif action == "toggle_play":
            mixer.toggle_play(song)
        elif action == "seek":
            mixer.seek(song, float(cmd["seconds"]))
        elif action == "seek_to":
            mixer.seek_to(song, float(cmd["fraction"]))
        elif action == "volume":
            mixer.set_volume(song, float(cmd["value"]))
        elif action == "pitch":
            mixer.set_pitch(song, float(cmd["value"]))
        elif action == "mark":
            self.mark(song)
        elif action == "remove_last_cue":
            track = mixer.tracks[song]
            if track is not None and mixer.remove_last_cue(song):
                save_cues(track.track_id, track.cues)
                self.status = "Deleted last cue."
        elif action == "remove_cue":
            slot = cmd["cue"]
            if not isinstance(slot, int) or not 0 <= slot < NUM_CUES:
                raise ValueError("bad cue")
            track = mixer.tracks[song]
            if track is not None:
                if mixer.remove_cue(song, slot):
                    save_cues(track.track_id, track.cues)
                    self.status = f"Deleted cue {slot + 1}. The rest are renumbered by position."
                else:
                    self.status = f"Cue {slot + 1} is not set."
        elif action == "load":
            source = str(cmd["source"]).strip().strip("'\"")
            if source:
                self.status = f"Loading song {song + 1}..."
                threading.Thread(target=self.load, args=(song, source), daemon=True).start()
        else:
            raise ValueError("bad action")

    def record(self, on: bool) -> None:
        if not on:
            stopped = self.mixer.stop_recording()
            if stopped is not None:
                self.status = f"Saved recording ({fmt_time(stopped[1])}): {stopped[0]}"
            return
        if self.mixer.recorded_frames() is not None:
            return
        stamp = time.strftime("PySamp-%Y%m%d-%H%M%S")
        path = RECORD_DIR / f"{stamp}.wav"
        number = 1
        while path.exists():
            number += 1
            path = RECORD_DIR / f"{stamp}-{number}.wav"
        try:
            RECORD_DIR.mkdir(parents=True, exist_ok=True)
            self.mixer.start_recording(path)
        except (OSError, RuntimeError) as exc:
            self.status = f"Could not start recording: {exc}"
            return
        self.status = "Recording the mix. Press \\ again to stop and save."

    def mark(self, song: int) -> None:
        track = self.mixer.tracks[song]
        if track is None:
            self.status = "No song in this slot."
            return
        pos = track.pos
        slot = self.mixer.mark_cue(song)
        if slot is None:
            self.status = f"All {NUM_CUES} cues used. Press backspace to delete the last one."
        else:
            save_cues(track.track_id, track.cues)
            self.status = f"Marked cue {slot + 1} at {fmt_time(pos)}."

    def load(self, song: int, source: str) -> None:
        try:
            track = load_source(source)
        except Exception as exc:
            lines = str(exc).strip().splitlines() or [type(exc).__name__]
            self.status = f"Could not load song {song + 1}: {lines[0][:120]}"
            return
        self.mixer.set_track(song, track)
        self.status = f"Loaded song {song + 1}: {track.title}."


class Handler(BaseHTTPRequestHandler):
    server: SamplerServer

    def log_message(self, *args) -> None:
        pass

    def reply(self, code: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized_path(self) -> str | None:
        url = urlparse(self.path)
        token = parse_qs(url.query).get("t", [""])[0]
        if not secrets.compare_digest(token, self.server.token):
            self.reply(403, b"forbidden", "text/plain")
            return None
        return url.path

    def do_GET(self) -> None:
        path = self.authorized_path()
        if path is None:
            return
        if path == "/":
            self.reply(200, (WEB_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/state":
            self.reply(200, json.dumps(self.server.state()).encode())
        elif path == "/events":
            self.stream_events()
        elif path.startswith("/peaks/") and path[7:].isdigit() and int(path[7:]) < NUM_SONGS:
            peaks = self.server.peaks(int(path[7:]))
            if peaks is None:
                self.reply(404, b"empty slot", "text/plain")
            else:
                self.reply(200, json.dumps(peaks).encode())
        else:
            self.reply(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        path = self.authorized_path()
        if path is None:
            return
        if path != "/cmd":
            self.reply(404, b"not found", "text/plain")
            return
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.server.command(json.loads(body))
        except (ValueError, KeyError, TypeError) as exc:
            self.reply(400, f"bad command: {exc}".encode(), "text/plain")
            return
        self.reply(200, b'{"ok": true}')

    def stream_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while not self.server.quit_event.is_set():
                self.wfile.write(f"data: {json.dumps(self.server.state())}\n\n".encode())
                self.wfile.flush()
                time.sleep(EVENT_INTERVAL)
        except OSError:
            pass
