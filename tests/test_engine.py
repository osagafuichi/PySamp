import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from pysamp.cuestore import load_cues, save_cues
from pysamp.engine import MAX_LAYERS, MAX_TAKES, MAX_VOICES, NUM_CUES, NUM_PADS, SAMPLE_RATE, Mixer, load_track

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


def test_shift_layers_cues_within_one_song():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        track = load_track(wav)
        mixer.set_track(0, track)
        for seconds in (1, 4, 7):
            mixer.seek_to(0, seconds / 10)
            mixer.mark_cue(0)

        mixer.trigger(0, 0)
        mixer.trigger(0, 1, layer=True)
        assert track.playing and track.layers == [track.cues[1]], "layered cue starts a second playhead"
        assert track.pos == track.cues[0], "main playhead does not jump"
        out = pull(mixer)
        expected = track.data[track.cues[0] : track.cues[0] + FRAMES] + track.data[track.cues[1] : track.cues[1] + FRAMES]
        assert np.allclose(out, expected, atol=1e-6), "both playheads are mixed"
        assert track.layers == [track.cues[1] + FRAMES] and track.pos == track.cues[0] + FRAMES

        mixer.trigger(0, 2)
        assert not track.layers and track.pos == track.cues[2], "plain trigger drops the layers"

        mixer.trigger(0, 0, layer=True)
        mixer.set_pitch(0, 2.0)
        out = pull(mixer)
        low = track.cues[0] + np.arange(FRAMES) * 2
        assert np.allclose(out[:, 0], track.data[low, 0] + track.data[track.cues[2] : track.cues[2] + FRAMES * 2 : 2, 0], atol=1e-4), "layers follow the pitch"
        mixer.set_pitch(0, 1.0)

        mixer.toggle_play(0)
        assert not track.playing and not track.layers, "pause drops the layers"
        mixer.trigger(0, 1, layer=True)
        assert track.playing and not track.layers and track.pos == track.cues[1], "Shift on a paused song just starts it"

        for _ in range(20):
            mixer.trigger(0, 0, layer=True)
        assert len(track.layers) == MAX_LAYERS
        mixer.stop_all()
        assert not track.layers and not pull(mixer).any(), "stop all silences the layers"

        track.cues[3] = len(track.data) - 100
        mixer.trigger(0, 2)
        mixer.trigger(0, 3, layer=True)
        for _ in range(2):
            pull(mixer)
        assert track.playing and not track.layers, "a layer ends with the audio"


def test_drum_hits():
    from pysamp import drums

    kit = drums.pads()
    assert len(kit) == NUM_PADS

    mixer = Mixer()
    assert not pull(mixer).any()
    kick = drums.NAMES.index("808 Kick")
    mixer.hit(kick)
    out = pull(mixer)
    np.testing.assert_allclose(out, kit[kick][0][:FRAMES])
    np.testing.assert_allclose(pull(mixer), kit[kick][0][FRAMES : 2 * FRAMES])

    mixer = Mixer()
    mixer.hit(NUM_PADS)
    mixer.hit(-1)
    assert not pull(mixer).any() and not mixer._voices, "bad pads are ignored"

    mixer.hit(kick)
    for _ in range(len(kit[kick][0]) // FRAMES + 2):
        pull(mixer)
    assert not mixer._voices, "finished voices are dropped"
    assert not pull(mixer).any()

    names = drums.NAMES
    open_hat, closed_hat, snare = names.index("Open Hat"), names.index("Closed Hat"), names.index("Snare")
    mixer.hit(open_hat)
    mixer.hit(snare)
    mixer.hit(closed_hat)
    kept = [v.data for v in mixer._voices]
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


def test_notes_play_and_release():
    from pysamp import instruments

    piano, organ = 0, 2
    assert instruments.INSTRUMENTS[organ].label == "Organ"
    mixer = Mixer()
    mixer.note_on(piano, 63)
    data, loop = instruments.note_data(piano, 63)
    assert loop is None
    np.testing.assert_allclose(pull(mixer), np.broadcast_to(data[:FRAMES], (FRAMES, 2)))
    np.testing.assert_allclose(pull(mixer), np.broadcast_to(data[FRAMES : 2 * FRAMES], (FRAMES, 2)))

    mixer = Mixer()
    mixer.note_on(piano, 63)
    mixer.note_on(piano, 64)
    mixer.note_off(piano, 63)
    release = int(instruments.INSTRUMENTS[piano].release * SAMPLE_RATE)
    for _ in range(release // FRAMES + 2):
        pull(mixer)
    assert [v.key for v in mixer._voices] == [64], "note_off fades out only its own key, then drops the voice"

    mixer = Mixer()
    mixer.note_on(piano, 63)
    before = pull(mixer)
    mixer.note_off(piano, 63)
    faded = pull(mixer)
    unfaded = np.broadcast_to(instruments.note_data(piano, 63)[0][FRAMES : 2 * FRAMES], (FRAMES, 2))
    assert np.abs(faded[-1]).max() < np.abs(unfaded[-1]).max() + 1e-9 and np.abs(faded).sum() < np.abs(unfaded).sum()
    assert before.any()

    mixer = Mixer()
    mixer.note_on(organ, 60)
    data, loop = instruments.note_data(organ, 60)
    assert loop is not None
    for _ in range(len(data) // FRAMES + 40):
        out = pull(mixer)
    assert out.any() and len(mixer._voices) == 1, "a looping note keeps sounding past the end of its sample"
    mixer.note_off(organ, 60)
    for _ in range(int(instruments.INSTRUMENTS[organ].release * SAMPLE_RATE) // FRAMES + 2):
        pull(mixer)
    assert not mixer._voices and not pull(mixer).any()

    mixer = Mixer()
    mixer.note_on(-1, 0)
    mixer.note_on(9, 0)
    mixer.note_on(piano, 47 - 12)
    mixer.note_on(piano, 48 + 12 * instruments.OCTAVE_MAX + instruments.KEYS)
    mixer.note_off(99, 0)
    assert not mixer._voices and not pull(mixer).any(), "bad presets and keys are ignored"

    mixer = Mixer()
    mixer.note_on(piano, 60, 1.0)
    full = pull(mixer)
    mixer = Mixer()
    mixer.note_on(piano, 60, 0.5)
    np.testing.assert_allclose(pull(mixer), full * 0.5, atol=1e-6)

    mixer = Mixer()
    for _ in range(MAX_VOICES + 10):
        mixer.note_on(piano, 60)
    assert len(mixer._voices) == MAX_VOICES


def test_recording_captures_the_mix():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        mixer.set_track(0, load_track(wav))
        assert mixer.recorded_frames() is None and mixer.stop_recording() is None

        pull(mixer)
        out = Path(d) / "take.wav"
        mixer.start_recording(out)
        assert mixer.recorded_frames() == 0
        mixer.toggle_play(0)
        mixer.hit(0)
        blocks = [pull(mixer) for _ in range(5)]
        assert mixer.recorded_frames() == 5 * FRAMES
        path, frames = mixer.stop_recording()
        assert path == out and frames == 5 * FRAMES and mixer.recorded_frames() is None
        pull(mixer)

        data, rate = sf.read(str(out), dtype="float32", always_2d=True)
        assert rate == SAMPLE_RATE and data.shape == (5 * FRAMES, 2)
        np.testing.assert_allclose(data, np.concatenate(blocks), atol=1e-4)
        assert np.abs(data).max() > 0.001, "the recording is not silent"

        again = Path(d) / "again.wav"
        mixer.start_recording(again)
        second = Path(d) / "second.wav"
        mixer.start_recording(second)
        pull(mixer)
        assert mixer.stop_recording()[0] == second
        assert sf.info(str(again)).frames == 0, "starting a new recording closes the old one"
        mixer.start_recording(Path(d) / "last.wav")
        mixer.stop()
        assert mixer.recorded_frames() is None, "stop() finishes an open recording"


def test_takes_play_seek_and_remove():
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        for _ in range(MAX_TAKES + 2):
            mixer.add_take(load_track(wav, "take"))
        assert len(mixer.takes) == MAX_TAKES, "the oldest takes drop off the list"
        assert not pull(mixer).any(), "a new take is silent until it is played"

        mixer.toggle_take(0)
        assert mixer.takes[0].playing and pull(mixer).any()
        mixer.toggle_take(0)
        assert not mixer.takes[0].playing
        mixer.toggle_take(99)
        mixer.seek_take(1, 0.5)
        assert mixer.takes[1].playing and mixer.takes[1].pos > 0, "seeking a take also plays it"
        mixer.seek_take(99, 0.5)
        mixer.stop_all()
        assert not any(t.playing for t in mixer.takes), "stop_all stops takes too"

        mixer.toggle_take(2)
        mixer.takes[2].pos = len(mixer.takes[2].data)
        mixer.takes[2].playing = False
        mixer.toggle_take(2)
        assert mixer.takes[2].pos == 0 and mixer.takes[2].playing, "a finished take restarts from the top"
        assert mixer.remove_take(0) and len(mixer.takes) == MAX_TAKES - 1
        assert not mixer.remove_take(MAX_TAKES) and not mixer.remove_take(-1)

        mixer = Mixer()
        mixer.add_take(load_track(wav, "take"))
        mixer.toggle_take(0)
        out = Path(d) / "layered.wav"
        mixer.start_recording(out)
        pull(mixer)
        assert mixer.level > 0, "level follows the mix while recording"
        mixer.stop_recording()
        assert mixer.level == 0
        assert np.abs(sf.read(str(out))[0]).max() > 0, "a playing take is part of the next recording"


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
    test_shift_layers_cues_within_one_song()
    test_drum_hits()
    test_drums_play_over_songs()
    test_notes_play_and_release()
    test_recording_captures_the_mix()
    test_takes_play_seek_and_remove()
    test_cue_store_roundtrip()
    print("engine tests passed")
