import numpy as np

from pysamp import drums
from pysamp.engine import SAMPLE_RATE


def test_kit_layout_and_levels():
    assert len(drums.NAMES) == 30 and len(set(drums.NAMES)) == 30
    kit = drums.pads()
    assert len(kit) == 30
    for name, (data, group) in zip(drums.NAMES, kit):
        assert data.dtype == np.float32 and data.ndim == 2 and data.shape[1] == 2, name
        assert np.isfinite(data).all(), name
        assert 0.02 * SAMPLE_RATE < len(data) < 2.5 * SAMPLE_RATE, name
        assert 0.15 < np.abs(data).max() <= 0.7 + 1e-6, name
        assert abs(data[-1]).max() < 1e-3, f"{name} ends without a click"
        np.testing.assert_array_equal(data[:, 0], data[:, 1])


def test_choke_groups_and_variety():
    kit = dict(zip(drums.NAMES, drums.pads()))
    hats = {kit[n][1] for n in ("Closed Hat", "Tight Hat", "Open Hat", "Pedal Hat")}
    assert len(hats) == 1 and hats != {0}, "all hats share one choke group"
    assert kit["808 Kick"][1] == 0 and kit["Snare"][1] == 0
    assert len(kit["Boom Kick"][0]) > len(kit["Tight Kick"][0])
    assert len(kit["Open Hat"][0]) > len(kit["Closed Hat"][0])
    sounds = {kit[n][0].tobytes() for n in drums.NAMES}
    assert len(sounds) == 30, "every pad sounds different"


if __name__ == "__main__":
    test_kit_layout_and_levels()
    test_choke_groups_and_variety()
    print("drum tests passed")
