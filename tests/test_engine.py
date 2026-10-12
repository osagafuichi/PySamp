import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from pysamp.cuestore import load_cues, save_cues
from pysamp.engine import MAX_VOICES, NUM_CUES, NUM_PADS, SAMPLE_RATE, Mixer, load_track

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


def test_remove_cue_renumbers_by_position():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        track = load_track(wav)
        mixer = Mixer()
        mixer.set_track(0, track)

        for seconds in (5, 2, 8, 2):
            mixer.seek_to(0, seconds / 10)
            mixer.mark_cue(0)
        s = SAMPLE_RATE
        assert track.cues[:4] == [5 * s, 2 * s, 8 * s, 2 * s]

        mixer.trigger(0, 2)
        assert track.active_cue == 2
        assert mixer.remove_cue(0, 0)
        assert track.cues[:4] == [2 * s, 2 * s, 8 * s, None], "sorted by position, packed to the front"
        assert track.cues[4:] == [None] * (NUM_CUES - 4)
        assert track.active_cue == 2, "active cue follows its position (8s)"

        assert mixer.remove_cue(0, 2)
        assert track.active_cue is None, "deleting the active cue clears it"
        assert track.cues[:3] == [2 * s, 2 * s, None]

        assert not mixer.remove_cue(0, 2), "slot already empty"
        assert not mixer.remove_cue(0, NUM_CUES) and not mixer.remove_cue(0, -1)
        assert not mixer.remove_cue(5, 0), "empty song"
        assert mixer.mark_cue(0) == 2, "next mark fills the first free slot"


def test_pitch():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        track = load_track(wav)
        mixer = Mixer()
        mixer.set_track(0, track)
        ramp = track.data[:, 0]

        def expect(start: float, rate: float) -> np.ndarray:
            return np.interp(start + np.arange(FRAMES) * rate, np.arange(len(ramp)), ramp)

        mixer.set_pitch(0, 2.0)
        mixer.seek(0, 1)
        mixer.toggle_play(0)
        out = pull(mixer)
        np.testing.assert_allclose(out[:, 0], expect(SAMPLE_RATE, 2.0), atol=1e-5)
        assert track.pos == SAMPLE_RATE + 2 * FRAMES

        mixer.set_pitch(0, 0.5)
        start = track.pos
        out = pull(mixer)
        np.testing.assert_allclose(out[:, 0], expect(start, 0.5), atol=1e-5)
        assert track.pos == start + FRAMES / 2

        mixer.set_volume(0, 0.5)
        start = track.pos
        np.testing.assert_allclose(pull(mixer)[:, 0], expect(start, 0.5) * 0.5, atol=1e-5)

        mixer.set_pitch(0, 1.0)
        mixer.seek_to(0, 0.5)
        start = int(track.pos)
        np.testing.assert_allclose(pull(mixer)[:, 0], ramp[start : start + FRAMES] * 0.5, atol=1e-6)

        mixer.set_pitch(0, 99)
        assert track.rate == 2.0
        mixer.set_pitch(0, 0)
        assert track.rate == 0.5
        mixer.set_pitch(5, 1.5)

        mixer.set_pitch(0, 2.0)
        mixer.set_volume(0, 1.0)
        track.pos = len(track.data) - FRAMES
        track.playing = True
        pull(mixer)
        assert not track.playing and track.pos == len(track.data), "stops at the end, no index error"
        assert not pull(mixer).any()

        track.pos = 1234.75
        mixer.mark_cue(0)
        assert track.cues[0] == 1234 and isinstance(track.cues[0], int)


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
            mixer.trigger(song, 0, layer=True)
        out = pull(mixer)
        assert out.max() <= 1.0 and out.min() >= -1.0, "mixed output is clipped"


def test_trigger_stops_other_songs_unless_layered():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        for song in (0, 1, 2):
            mixer.set_track(song, load_track(wav))
            mixer.seek(song, 1)
            mixer.mark_cue(song)
        mixer.tracks[2].cues[0] = None

        mixer.trigger(0, 0)
        mixer.trigger(1, 0, layer=True)
        assert mixer.tracks[0].playing and mixer.tracks[1].playing, "Shift keeps both playing"

        pos0 = mixer.tracks[0].pos
        mixer.trigger(1, 0)
        assert mixer.tracks[1].playing and not mixer.tracks[0].playing, "plain trigger stops the other"
        assert mixer.tracks[0].pos == pos0, "stopped song keeps its position"

        mixer.trigger(0, 0, layer=True)
        mixer.trigger(2, 0)
        assert mixer.tracks[0].playing and mixer.tracks[1].playing, "empty cue stops nothing"

        mixer.trigger(1, 0)
        assert mixer.tracks[1].playing and not mixer.tracks[0].playing
        mixer.trigger(1, 0)
        assert mixer.tracks[1].playing, "re-trigger on the same song keeps it playing"


def test_drum_hits():
    from pysamp import drums

    kit = drums.pads()
    assert len(kit) == NUM_PADS

    mixer = Mixer()
    assert not pull(mixer).any()
    mixer.hit(30)
    out = pull(mixer)
    np.testing.assert_allclose(out, kit[30][0][:FRAMES])
    np.testing.assert_allclose(pull(mixer), kit[30][0][FRAMES : 2 * FRAMES])

    mixer = Mixer()
    mixer.hit(NUM_PADS)
    mixer.hit(-1)
    assert not pull(mixer).any() and not mixer._voices, "bad pads are ignored"

    mixer.hit(30)
    for _ in range(len(kit[30][0]) // FRAMES + 2):
        pull(mixer)
    assert not mixer._voices, "finished voices are dropped"
    assert not pull(mixer).any()

    names = drums.NAMES
    open_hat, closed_hat, snare = names.index("Open Hat"), names.index("Closed Hat"), names.index("Snare")
    mixer.hit(open_hat)
    mixer.hit(snare)
    mixer.hit(closed_hat)
    kept = [v[0] for v in mixer._voices]
    assert len(kept) == 2 and kept[0] is kit[snare][0] and kept[1] is kit[closed_hat][0], "closed hat cuts the open hat"

    mixer = Mixer()
    for _ in range(MAX_VOICES + 10):
        mixer.hit(names.index("808 Kick"))
    assert len(mixer._voices) == MAX_VOICES
    out = pull(mixer)
    assert out.max() <= 1.0 and out.min() >= -1.0, "stacked drums are clipped"


def test_drums_play_over_songs():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        track = load_track(wav)
        mixer.set_track(0, track)
        mixer.seek(0, 1)
        mixer.mark_cue(0)
        mixer.trigger(0, 0)
        mixer.hit(0)
        from pysamp import drums

        expected = track.data[SAMPLE_RATE : SAMPLE_RATE + FRAMES] + drums.pads()[0][0][:FRAMES]
        np.testing.assert_allclose(pull(mixer), np.clip(expected, -1, 1), atol=1e-6)
        mixer.trigger(0, 0)
        mixer.stop_all()
        mixer.hit(1)
        assert pull(mixer).any(), "stop_all leaves drums alone"


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
    test_remove_cue_renumbers_by_position()
    test_pitch()
    test_empty_row_and_clipping()
    test_trigger_stops_other_songs_unless_layered()
    test_drum_hits()
    test_drums_play_over_songs()
    test_cue_store_roundtrip()
    print("engine tests passed")
