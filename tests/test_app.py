import asyncio
import tempfile
from pathlib import Path

from pysamp.app import SamplerApp
from pysamp.engine import Mixer, load_track
from test_engine import make_ramp_wav


async def run() -> None:
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav)
        mixer = Mixer()
        mixer.set_track(0, load_track(wav, "row one"))
        mixer.set_track(1, load_track(wav, "row two"))

        app = SamplerApp(mixer)
        async with app.run_test() as pilot:
            await pilot.press("e")
            assert mixer.tracks[1].playing and mixer.tracks[1].active_cue == 2
            assert not mixer.tracks[0].playing
            assert app.selected == 1

            await pilot.press("semicolon")
            assert mixer.tracks[2] is None and app.selected == 2

            await pilot.press("up")
            assert app.selected == 1
            await pilot.press("left")
            assert abs(mixer.tracks[1].volume - 0.95) < 1e-6

            await pilot.press("up")
            await pilot.press("1")
            assert mixer.tracks[0].playing and mixer.tracks[0].active_cue == 0

            await pilot.press("space")
            assert not mixer.tracks[0].playing and not mixer.tracks[1].playing


if __name__ == "__main__":
    asyncio.run(run())
    print("app tests passed")
