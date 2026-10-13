import numpy as np

from pysamp import instruments as ins
from pysamp.engine import SAMPLE_RATE


def test_ranges_and_names():
    piano, bass = ins.INSTRUMENTS[0], ins.INSTRUMENTS[5]
    assert ins.note_name(60) == "C4" and ins.note_name(70) == "Bb4"
    assert len({i.id for i in ins.INSTRUMENTS}) == len(ins.INSTRUMENTS) == 9
    assert (ins.midi_range(piano).start, ins.midi_range(piano).stop) == (36, 90), "C2 up to F6 over four octave positions"
    assert ins.midi_range(bass).start == 24


def test_every_sample_is_bundled_and_renders():
    for index, instrument in enumerate(ins.INSTRUMENTS):
        for midi in ins.sample_notes(instrument):
            assert (ins.SAMPLES_DIR / instrument.id / f"{ins.note_name(midi)}.ogg").is_file(), (instrument.id, midi)
        for midi in (ins.midi_range(instrument)[0], instrument.base, ins.midi_range(instrument)[-1]):
            data, loop = ins.note_data(index, midi)
            label = (instrument.id, midi)
            assert data.dtype == np.float32 and data.ndim == 2 and data.shape[1] == 1, label
            assert np.isfinite(data).all(), label
            assert SAMPLE_RATE < len(data) < 6 * SAMPLE_RATE, label
            assert 0.2 < np.abs(data).max() <= ins.PEAK + 1e-6, label
            if instrument.loop:
                start, stop = loop
                assert stop == len(data) and 0 < start < stop, label
                assert abs(data[stop - 1, 0] - data[start - 1, 0]) < 1e-6, f"{label} loops without a jump"
            else:
                assert loop is None and abs(data[-1, 0]) < 1e-3, f"{label} ends without a click"
        ins.warm(index)
        assert ins.note_data(index, instrument.base) is ins.note_data(index, instrument.base), "notes render once"


def test_cache_keeps_a_few_instruments():
    for index in range(len(ins.INSTRUMENTS)):
        ins.warm(index)
    assert len(ins._cache) == ins.CACHE_SIZE


def fundamental(data: np.ndarray) -> float:
    window = data[SAMPLE_RATE // 20 : SAMPLE_RATE // 20 + SAMPLE_RATE // 2, 0]
    spectrum = np.fft.rfft(window, 2 * len(window))
    corr = np.fft.irfft(np.abs(spectrum) ** 2)
    lags = np.arange(SAMPLE_RATE // 600, SAMPLE_RATE // 80)
    return SAMPLE_RATE / lags[corr[lags].argmax()]


def test_pitch_is_shifted_toward_the_key():
    low, high = fundamental(ins.note_data(0, 48)[0]), fundamental(ins.note_data(0, 60)[0])
    assert abs(low / 130.8 - 1) < 0.03 and abs(high / 261.6 - 1) < 0.03, (low, high)
    shifted_up = fundamental(ins.note_data(0, 62)[0])
    assert abs(shifted_up / 293.7 - 1) < 0.03, "keys between the stored samples are pitch-shifted"


if __name__ == "__main__":
    test_ranges_and_names()
    test_every_sample_is_bundled_and_renders()
    test_cache_keeps_a_few_instruments()
    test_pitch_is_shifted_toward_the_key()
    print("instrument tests passed")
