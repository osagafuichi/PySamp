import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

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


def test_cue_jump_and_volume():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        track = load_track(wav)
        assert len(track.cues) == NUM_CUES

        mixer = Mixer()
        mixer.set_track(0, track)

        assert not pull(mixer).any(), "silent before trigger"

        mixer.trigger(0, 3)
        out = pull(mixer)
        expected = track.data[track.cues[3] : track.cues[3] + FRAMES]
        np.testing.assert_allclose(out, expected, atol=1e-6)

        mixer.trigger(0, 3)
        mixer.set_volume(0, 0.5)
        out = pull(mixer)
        np.testing.assert_allclose(out, expected * 0.5, atol=1e-6)

        mixer.stop_all()
        assert not pull(mixer).any(), "silent after stop_all"


def test_empty_row_and_clipping():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        mixer.trigger(2, 0)
        assert not pull(mixer).any(), "empty row ignored"

        mixer.set_track(0, load_track(wav))
        mixer.set_track(1, load_track(wav))
        mixer.trigger(0, NUM_CUES - 1)
        mixer.trigger(1, NUM_CUES - 1)
        out = pull(mixer)
        assert out.max() <= 1.0 and out.min() >= -1.0, "mixed output is clipped"


if __name__ == "__main__":
    test_cue_jump_and_volume()
    test_empty_row_and_clipping()
    print("engine tests passed")
