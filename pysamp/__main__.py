import sys

from pysamp.app import SamplerApp
from pysamp.engine import NUM_SONGS, Mixer
from pysamp.loader import load_source


def prompt_for_sources() -> list[str]:
    print(f"PySamp: paste up to {NUM_SONGS} YouTube links or audio file paths, one per line.")
    print("Songs 1-4 are bank A, songs 5-8 are bank B.")
    print("Press Enter on an empty line to start. You can load more songs inside the app with Ctrl+O.\n")
    sources: list[str] = []
    while len(sources) < NUM_SONGS:
        source = input(f"Song {len(sources) + 1}: ").strip().strip("'\"")
        if not source:
            break
        sources.append(source)
    return sources


def main() -> None:
    sources = sys.argv[1:] or prompt_for_sources()
    if len(sources) > NUM_SONGS:
        sys.exit(f"Too many songs. Maximum is {NUM_SONGS}. Usage: pysamp [SOURCE ...]")

    mixer = Mixer()
    for song, source in enumerate(sources):
        print(f"[{song + 1}/{len(sources)}] loading {source}")
        try:
            mixer.set_track(song, load_source(source))
        except Exception as exc:
            sys.exit(f"Could not load {source}\n{exc}")

    mixer.start()
    try:
        SamplerApp(mixer).run()
    finally:
        mixer.stop()


if __name__ == "__main__":
    main()
