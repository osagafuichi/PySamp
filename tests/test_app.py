import asyncio
import tempfile
from pathlib import Path

from textual import events

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
        for song in (0, 1, 4, 5):
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

            # Selector keys pick a song in the current bank without playing it.
            await pilot.press("q")
            assert app.selected == 1 and not mixer.tracks[1].playing
            await pilot.press("1")
            assert app.selected == 0

            # Tab moves to bank B (songs 5-8) and selects song 5; selectors follow the bank.
            await pilot.press("tab")
            assert app.bank == 1 and app.selected == 4
            await pilot.press("q")
            assert app.selected == 5
            await pilot.press("1")
            await pilot.press("right")
            await pilot.press("right")
            await pilot.press("m")
            assert mixer.tracks[4].cues[0] == 10 * SAMPLE_RATE

            # Backtick moves to page 2.
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

            # Play mode: cue keys trigger bank/page-aware cues.
            await pilot.press("enter")
            assert app.mode == "play"
            await pilot.press("tab")
            assert app.bank == 0
            await pilot.press("grave_accent")
            assert app.page == 0
            await pilot.press("3")
            assert mixer.tracks[0].playing and mixer.tracks[0].active_cue == 1
            assert mixer.tracks[0].pos == 5 * SAMPLE_RATE

            # Unset cue does nothing, selector keys never play, empty cue on another song does nothing.
            await pilot.press("4")
            assert mixer.tracks[0].active_cue == 1
            await pilot.press("q")
            assert app.selected == 1 and not mixer.tracks[1].playing
            await pilot.press("e")
            assert not mixer.tracks[1].playing

            # Cue 9 is the last key of page 1 (0); cue 10 is the first key of page 2 (2).
            mixer.stop_all()
            mixer.tracks[0].cues[8] = 7 * SAMPLE_RATE
            mixer.tracks[0].cues[9] = 9 * SAMPLE_RATE
            await pilot.press("1")
            await pilot.press("0")
            assert mixer.tracks[0].active_cue == 8 and mixer.tracks[0].pos == 7 * SAMPLE_RATE
            await pilot.press("grave_accent")
            await pilot.press("2")
            assert mixer.tracks[0].active_cue == 9 and mixer.tracks[0].pos == 9 * SAMPLE_RATE

            # Volume in play mode applies to the selected song.
            mixer.stop_all()
            await pilot.press("1")
            await pilot.press("left")
            assert abs(mixer.tracks[0].volume - 0.95) < 1e-6

            await pilot.press("grave_accent")
            await pilot.press("2")
            assert mixer.tracks[0].playing
            await pilot.press("space")
            assert not mixer.tracks[0].playing


def wheel(kind, x=0, y=0):
    return kind(None, x, y, 0, 0, 0, False, False, False, x, y)


async def run_scroll() -> None:
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav, seconds=5)
        mixer = Mixer()
        for song in (0, 1, 5):
            mixer.set_track(song, load_track(wav, f"song {song + 1}"))

        app = SamplerApp(mixer)
        async with app.run_test() as pilot:
            # Wheel events enter at the app, are routed to the widget under the pointer,
            # and must bubble back up. The pointer sits over row 4, never the selected song.
            region = app.query_one("#row3").region

            async def scroll(kind, times=1):
                for _ in range(times):
                    app.post_message(wheel(kind, region.x + 1, region.y))
                await pilot.pause()

            await scroll(events.MouseScrollUp)
            assert mixer.tracks[0].volume == 1.0, "clamped at 1"
            await scroll(events.MouseScrollDown, 3)
            assert abs(mixer.tracks[0].volume - 0.94) < 1e-6

            await pilot.press("q")
            await scroll(events.MouseScrollDown)
            assert abs(mixer.tracks[1].volume - 0.98) < 1e-6
            assert abs(mixer.tracks[0].volume - 0.94) < 1e-6, "other songs untouched"

            await scroll(events.MouseScrollLeft, 100)
            assert mixer.tracks[1].volume == 0.0, "clamped at 0"
            await scroll(events.MouseScrollRight)
            assert abs(mixer.tracks[1].volume - 0.02) < 1e-6

            await pilot.press("a")
            await scroll(events.MouseScrollDown)
            assert mixer.tracks[2] is None, "empty slot ignored"

            await pilot.press("tab")
            await pilot.press("q")
            assert app.selected == 5
            await scroll(events.MouseScrollDown, 2)
            assert abs(mixer.tracks[5].volume - 0.96) < 1e-6


async def run_load() -> None:
    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "ramp.wav"
        make_ramp_wav(wav, seconds=5)

        def fake_load(source):
            if source == "bad":
                raise RuntimeError("ERROR: no such video\nsecond line")
            return load_track(wav, f"loaded {source}")

        app_module.load_source = fake_load
        mixer = Mixer()
        mixer.set_track(0, load_track(wav, "first"))
        app = SamplerApp(mixer)
        async with app.run_test() as pilot:
            box = app.query_one("#loader")
            assert not box.display

            # Select an empty slot and open the loader.
            await pilot.press("a")
            assert app.selected == 2 and mixer.tracks[2] is None
            await pilot.press("ctrl+o")
            assert app.loading and box.display

            # Keys go to the text box, not the sampler.
            await pilot.press("q")
            assert box.value == "q" and app.selected == 2
            await pilot.press("tab")
            assert app.bank == 0

            # Load into the selected empty slot.
            box.value = "song.wav"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not app.loading and not box.display
            assert mixer.tracks[2] is not None and mixer.tracks[2].title == "loaded song.wav"
            assert app.status.startswith("Loaded song 3")

            # Sampler keys work again afterwards.
            await pilot.press("q")
            assert app.selected == 1

            # Escape cancels without loading.
            await pilot.press("z")
            await pilot.press("ctrl+o")
            await pilot.press("escape")
            assert not app.loading and not box.display and mixer.tracks[3] is None
            assert app.status == "Load cancelled."

            # A failed load reports the error and leaves the slot empty.
            await pilot.press("ctrl+o")
            box.value = "bad"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert mixer.tracks[3] is None
            assert app.status == "Could not load song 4: ERROR: no such video"

            # Loading into an occupied slot replaces it.
            await pilot.press("1")
            await pilot.press("ctrl+o")
            box.value = "other.wav"
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            assert mixer.tracks[0].title == "loaded other.wav"


if __name__ == "__main__":
    asyncio.run(run())
    asyncio.run(run_scroll())
    asyncio.run(run_load())
    print("app tests passed")
