import json
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pysamp.server as server_module
from pysamp.engine import NUM_CUES, NUM_PADS, SAMPLE_RATE, Mixer, load_track
from test_engine import make_ramp_wav


class Client:
    def __init__(self, srv):
        self.base = f"http://127.0.0.1:{srv.server_port}"
        self.token = srv.token

    def get(self, path, token=True):
        url = self.base + path + (f"?t={self.token}" if token else "")
        with urllib.request.urlopen(url) as response:
            return response.read()

    def get_json(self, path):
        return json.loads(self.get(path))

    def post(self, cmd):
        request = urllib.request.Request(
            f"{self.base}/cmd?t={self.token}", data=json.dumps(cmd).encode(), method="POST"
        )
        with urllib.request.urlopen(request) as response:
            return response.status

    def song(self, index):
        return self.get_json("/state")["songs"][index]

    def status(self):
        return self.get_json("/state")["status"]


def status_of(call):
    try:
        call()
    except urllib.error.HTTPError as exc:
        return exc.code
    return 200


def wait_for(check, seconds=5.0):
    deadline = time.time() + seconds
    while time.time() < deadline:
        if check():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def run() -> None:
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav, seconds=10)
        saved = []
        server_module.save_cues = lambda track_id, cues, *a, **k: saved.append(list(cues))

        def fake_load(source):
            if source == "bad":
                raise RuntimeError("ERROR: no such video\nsecond line")
            return load_track(wav, f"loaded {source}", track_id=source)

        server_module.load_source = fake_load

        mixer = Mixer()
        mixer.set_track(0, load_track(wav, "first"))
        srv = server_module.SamplerServer(mixer)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        c = Client(srv)

        # Requests without the right token are rejected.
        assert status_of(lambda: c.get("/state", token=False)) == 403
        assert status_of(lambda: urllib.request.urlopen(f"{c.base}/state?t=wrong")) == 403
        assert status_of(
            lambda: urllib.request.urlopen(
                urllib.request.Request(f"{c.base}/cmd", data=b'{"action": "stop_all"}', method="POST")
            )
        ) == 403

        # The page itself is served.
        page = c.get("/").decode()
        assert "<title>PySamp</title>" in page and "EventSource" in page

        # State shape.
        state = c.get_json("/state")
        assert state["rate"] == SAMPLE_RATE and len(state["songs"]) == 8
        assert state["songs"][1] == {"loaded": False}
        first = state["songs"][0]
        assert first["loaded"] and first["title"] == "first" and first["total"] == 10 * SAMPLE_RATE
        assert first["volume"] == 1.0 and first["cues"] == [None] * NUM_CUES

        # Unset cue does nothing; seek_to, mark, seek, mark, trigger.
        c.post({"action": "trigger", "song": 0, "cue": 0})
        assert not c.song(0)["playing"]
        c.post({"action": "seek_to", "song": 0, "fraction": 0.1})
        assert c.song(0)["pos"] == SAMPLE_RATE
        c.post({"action": "mark", "song": 0})
        assert c.song(0)["cues"][0] == SAMPLE_RATE and c.status() == "Marked cue 1 at 0:01."
        c.post({"action": "seek", "song": 0, "seconds": 2})
        c.post({"action": "mark", "song": 0})
        assert c.song(0)["cues"][:2] == [SAMPLE_RATE, 3 * SAMPLE_RATE]
        assert len(saved) == 2, "cues are saved on every mark"
        c.post({"action": "seek_to", "song": 0, "fraction": 0.9})
        c.post({"action": "trigger", "song": 0, "cue": 1})
        playing = c.song(0)
        assert playing["playing"] and playing["active_cue"] == 1 and playing["pos"] == 3 * SAMPLE_RATE

        # Volume clamps; play toggles; cue removal saves; stop_all.
        c.post({"action": "volume", "song": 0, "value": 5})
        assert c.song(0)["volume"] == 1.0
        c.post({"action": "volume", "song": 0, "value": -1})
        assert c.song(0)["volume"] == 0.0
        c.post({"action": "volume", "song": 0, "value": 0.5})
        assert c.song(0)["volume"] == 0.5
        assert c.song(0)["pitch"] == 1.0
        c.post({"action": "pitch", "song": 0, "value": 1.25})
        assert c.song(0)["pitch"] == 1.25
        c.post({"action": "pitch", "song": 0, "value": 9})
        assert c.song(0)["pitch"] == 2.0
        c.post({"action": "pitch", "song": 0, "value": 0})
        assert c.song(0)["pitch"] == 0.5
        c.post({"action": "pitch", "song": 0, "value": 1})
        c.post({"action": "toggle_play", "song": 0})
        assert not c.song(0)["playing"]
        c.post({"action": "remove_last_cue", "song": 0})
        assert c.song(0)["cues"][1] is None and len(saved) == 3
        c.post({"action": "toggle_play", "song": 0})
        c.post({"action": "stop_all"})
        assert not c.song(0)["playing"]

        # Deleting one cue renumbers the rest by position.
        for fraction in (0.5, 0.2):
            c.post({"action": "seek_to", "song": 0, "fraction": fraction})
            c.post({"action": "mark", "song": 0})
        assert c.song(0)["cues"][:3] == [SAMPLE_RATE, 5 * SAMPLE_RATE, 2 * SAMPLE_RATE]
        before = len(saved)
        c.post({"action": "remove_cue", "song": 0, "cue": 1})
        assert c.song(0)["cues"][:3] == [SAMPLE_RATE, 2 * SAMPLE_RATE, None]
        assert len(saved) == before + 1 and c.status().startswith("Deleted cue 2.")
        c.post({"action": "remove_cue", "song": 0, "cue": 5})
        assert c.status() == "Cue 6 is not set." and len(saved) == before + 1
        c.post({"action": "remove_cue", "song": 3, "cue": 0})

        # Trigger stops the other songs unless layer is true.
        mixer.set_track(4, load_track(wav, "second"))
        c.post({"action": "mark", "song": 4})
        c.post({"action": "trigger", "song": 4, "cue": 0})
        c.post({"action": "trigger", "song": 0, "cue": 0, "layer": True})
        assert c.song(0)["playing"] and c.song(4)["playing"]
        c.post({"action": "trigger", "song": 0, "cue": 0})
        assert c.song(0)["playing"] and not c.song(4)["playing"]
        c.post({"action": "stop_all"})

        # Drum pads: names are listed, hits start a voice, bad pads give 400.
        names = c.get_json("/state")["drum_names"]
        assert len(names) == NUM_PADS and names[0] == "Cowbell" and names[30] == "808 Kick"
        assert not mixer._voices
        c.post({"action": "drum", "pad": 0})
        c.post({"action": "drum", "pad": NUM_PADS - 1})
        assert len(mixer._voices) == 2
        mixer._voices.clear()

        # Marking in an empty slot reports it; a full song reports it.
        c.post({"action": "mark", "song": 3})
        assert c.status() == "No song in this slot."
        for _ in range(NUM_CUES):
            c.post({"action": "mark", "song": 0})
        assert c.status().startswith(f"All {NUM_CUES} cues used")

        # Bad commands give 400.
        assert status_of(lambda: c.post({"action": "nope", "song": 0})) == 400
        assert status_of(lambda: c.post({"action": "mark", "song": 99})) == 400
        assert status_of(lambda: c.post({"action": "pitch", "song": 0, "value": "fast"})) == 400
        assert status_of(lambda: c.post({"action": "pitch", "song": 0})) == 400
        assert status_of(lambda: c.post({"action": "trigger", "song": 0})) == 400
        assert status_of(lambda: c.post({"action": "trigger", "song": 0, "cue": 0, "layer": "yes"})) == 400
        assert status_of(lambda: c.post({"action": "drum", "pad": NUM_PADS})) == 400
        assert status_of(lambda: c.post({"action": "drum", "pad": -1})) == 400
        assert status_of(lambda: c.post({"action": "drum", "pad": "1"})) == 400
        assert status_of(lambda: c.post({"action": "drum"})) == 400
        assert status_of(lambda: c.post({"action": "remove_cue", "song": 0})) == 400
        assert status_of(lambda: c.post({"action": "remove_cue", "song": 0, "cue": NUM_CUES})) == 400
        assert status_of(lambda: c.post({"action": "remove_cue", "song": 0, "cue": "1"})) == 400
        assert status_of(lambda: c.post([1, 2])) == 400

        # Waveform peaks.
        peaks = c.get_json("/peaks/0")
        assert len(peaks["min"]) == len(peaks["max"]) == 1000
        assert peaks["max"][0] < 0.01 and 0.85 < peaks["max"][-1] <= 0.9
        assert all(lo <= hi for lo, hi in zip(peaks["min"], peaks["max"]))
        assert status_of(lambda: c.get("/peaks/1")) == 404
        assert status_of(lambda: c.get("/peaks/99")) == 404

        # Loading: success fills the slot, failure reports the first error line.
        c.post({"action": "load", "song": 2, "source": "  'ok.wav' "})
        wait_for(lambda: c.song(2)["loaded"])
        assert c.song(2)["title"] == "loaded ok.wav" and c.status() == "Loaded song 3: loaded ok.wav."
        c.post({"action": "load", "song": 3, "source": "bad"})
        wait_for(lambda: c.status().startswith("Could not load"))
        assert c.status() == "Could not load song 4: ERROR: no such video"
        assert not c.song(3)["loaded"]

        # The event stream pushes the same state.
        with urllib.request.urlopen(f"{c.base}/events?t={c.token}") as stream:
            line = stream.readline().decode()
        assert line.startswith("data: ") and len(json.loads(line[6:])["songs"]) == 8

        # Quit.
        assert not srv.quit_event.is_set()
        c.post({"action": "quit"})
        assert srv.quit_event.is_set()

        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    run()
    print("server tests passed")
