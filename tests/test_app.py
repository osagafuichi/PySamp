import asyncio
import tempfile
from pathlib import Path

import pysamp.app as app_module
from pysamp.app import SamplerApp
from pysamp.engine import SAMPLE_RATE, Mixer, load_track
from test_engine import make_ramp_wav


async def run() -> None:
    with tempfile.TemporaryDirectory() as d:
        app_module.save_cues = lambda *args, **kwargs: None
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav, seconds=60)
        mixer = Mixer()
        for song in (0, 1, 4):
            mixer.set_track(song, load_track(wav, f"song {song + 1}"))

        app = SamplerApp(mixer)
        async with app.run_test() as pilot:
            assert app.mode == "edit"

            # Edit mode: mark two cues on song 1 with a seek in between.
            await pilot.press("m")
            assert mixer.tracks[0].cues[0] == 0
            await pilot.press("right")
            await pilot.press("m")
            assert mixer.tracks[0].cues[1] == 5 * SAMPLE_RATE

            # Space plays and pauses the selected song.
            await pilot.press("space")
            assert mixer.tracks[0].playing
            await pilot.press("space")
            assert not mixer.tracks[0].playing

            # Tab moves to bank B (songs 5-8) and selects song 5.
            await pilot.press("tab")
            assert app.bank == 1 and app.selected == 4
            await pilot.press("right")
            await pilot.press("right")
            await pilot.press("m")
            assert mixer.tracks[4].cues[0] == 10 * SAMPLE_RATE

            # Backtick moves to page 2, and marks fill from slot 0 until slots run out.
            await pilot.press("grave_accent")
            assert app.page == 1

            # Up/down crosses banks.
            await pilot.press("up")
            assert app.selected == 3 and app.bank == 0
            await pilot.press("down")
            assert app.selected == 4 and app.bank == 1

            # Backspace deletes the last cue.
            await pilot.press("backspace")
            assert mixer.tracks[4].cues[0] is None

            # Play mode: row keys trigger bank/page-aware cues.
            await pilot.press("enter")
            assert app.mode == "play"
            await pilot.press("tab")
            assert app.bank == 0
            await pilot.press("grave_accent")
            assert app.page == 0
            await pilot.press("2")
            assert mixer.tracks[0].playing and mixer.tracks[0].active_cue == 1
            assert mixer.tracks[0].pos == 5 * SAMPLE_RATE

            # Unset cue and empty song do nothing.
            await pilot.press("3")
            assert mixer.tracks[0].active_cue == 1
            await pilot.press("q", "w")
            assert not mixer.tracks[1].playing

            # Page 2 maps to cues 11-20 (all unset here), so triggers do nothing.
            mixer.stop_all()
            await pilot.press("grave_accent")
            await pilot.press("1")
            assert not mixer.tracks[0].playing

            # Volume in play mode.
            await pilot.press("left")
            assert abs(mixer.tracks[0].volume - 0.95) < 1e-6

            await pilot.press("grave_accent")
            await pilot.press("1")
            assert mixer.tracks[0].playing
            await pilot.press("space")
            assert not mixer.tracks[0].playing


if __name__ == "__main__":
    asyncio.run(run())
    print("app tests passed")
