import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from pysamp.cuestore import load_cues, save_cues
from pysamp.engine import NUM_CUES, SAMPLE_RATE, Mixer, load_track

FRAMES = 256


def make_ramp_wav(path: Path, seconds: int = 10) -> None:
    n = SAMPLE_RATE * seconds
    ramp = np.linspace(0, 0.9, n, dtype="float32")
    sf.write(str(path), np.stack([ramp, ramp], axis=1), SAMPLE_RATE)


def pull(mixer: Mixer) -> np.ndarray:
    out = np.zeros((FRAMES, 2), dtype="float32")
    mixer._callback(out, FRAMES, None, None)
    return out


def test_mark_trigger_and_volume():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        track = load_track(wav)
        assert track.cues == [None] * NUM_CUES

        mixer = Mixer()
        mixer.set_track(0, track)

        mixer.trigger(0, 0)
        assert not pull(mixer).any(), "unset cue does nothing"

        mixer.seek(0, 1)
        assert mixer.mark_cue(0) == 0
        mixer.seek(0, 2)
        assert mixer.mark_cue(0) == 1
        assert track.cues[:2] == [SAMPLE_RATE, 3 * SAMPLE_RATE]

        mixer.trigger(0, 1)
        out = pull(mixer)
        expected = track.data[3 * SAMPLE_RATE : 3 * SAMPLE_RATE + FRAMES]
        np.testing.assert_allclose(out, expected, atol=1e-6)

        mixer.trigger(0, 1)
        mixer.set_volume(0, 0.5)
        np.testing.assert_allclose(pull(mixer), expected * 0.5, atol=1e-6)

        mixer.stop_all()
        assert not pull(mixer).any(), "silent after stop_all"


def test_toggle_seek_and_cue_limits():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        track = load_track(wav)
        mixer = Mixer()
        mixer.set_track(3, track)

        mixer.toggle_play(3)
        assert track.playing
        pull(mixer)
        assert track.pos == FRAMES
        mixer.toggle_play(3)
        assert not track.playing

        mixer.seek(3, -100)
        assert track.pos == 0
        mixer.seek(3, 1000)
        assert track.pos == len(track.data) - 1

        mixer.seek_to(3, 0.5)
        assert track.pos == len(track.data) // 2
        mixer.seek_to(3, -1)
        assert track.pos == 0
        mixer.seek_to(3, 2)
        assert track.pos == len(track.data) - 1
        mixer.seek_to(5, 0.5)

        for expected in range(NUM_CUES):
            assert mixer.mark_cue(3) == expected
        assert NUM_CUES == 18
        assert mixer.mark_cue(3) is None, "full at 18 cues"

        assert mixer.remove_last_cue(3)
        assert track.cues[NUM_CUES - 1] is None and track.cues[NUM_CUES - 2] is not None
        assert mixer.mark_cue(3) == NUM_CUES - 1

        assert mixer.mark_cue(5) is None and not mixer.remove_last_cue(5), "empty song"


def test_empty_row_and_clipping():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        mixer.trigger(2, 0)
        assert not pull(mixer).any(), "empty row ignored"

        for song in (0, 1):
            mixer.set_track(song, load_track(wav))
            mixer.seek(song, 9)
            mixer.mark_cue(song)
            mixer.trigger(song, 0)
        out = pull(mixer)
        assert out.max() <= 1.0 and out.min() >= -1.0, "mixed output is clipped"


def test_cue_store_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        cue_dir = Path(d)
        assert load_cues("abc", cue_dir) == [None] * NUM_CUES, "missing file gives empty cues"
        cues = [None] * NUM_CUES
        cues[0], cues[7], cues[NUM_CUES - 1] = 100, 5000, 123456
        save_cues("abc", cues, cue_dir)
        assert load_cues("abc", cue_dir) == cues
        (cue_dir / "bad.json").write_text("not json")
        assert load_cues("bad", cue_dir) == [None] * NUM_CUES, "corrupt file gives empty cues"


if __name__ == "__main__":
    test_mark_trigger_and_volume()
    test_toggle_seek_and_cue_limits()
    test_empty_row_and_clipping()
    test_cue_store_roundtrip()
    print("engine tests passed")
