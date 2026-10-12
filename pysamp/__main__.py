import sys
from pathlib import Path

from pysamp.app import SamplerApp
from pysamp.cuestore import load_cues
from pysamp.downloader import download
from pysamp.engine import NUM_SONGS, Mixer, load_track

DOWNLOAD_DIR = Path.home() / "PySamp" / "downloads"


def prompt_for_sources() -> list[str]:
    print(f"PySamp: paste up to {NUM_SONGS} YouTube links or audio file paths, one per line.")
    print("Songs 1-4 are bank A, songs 5-8 are bank B. Press Enter on an empty line when done.\n")
    sources: list[str] = []
    while len(sources) < NUM_SONGS:
        source = input(f"Song {len(sources) + 1}: ").strip().strip("'\"")
        if not source:
            break
        sources.append(source)
    return sources


def load_source(source: str):
    local = Path(source).expanduser()
    if local.is_file():
        return load_track(local, track_id=f"{local.stem}-{local.stat().st_size}")
    path, title = download(source, DOWNLOAD_DIR)
    return load_track(path, title)


def main() -> None:
    sources = sys.argv[1:] or prompt_for_sources()
    if not sources or len(sources) > NUM_SONGS:
        sys.exit(f"Need 1-{NUM_SONGS} songs. Usage: pysamp SOURCE [SOURCE ...]")

    mixer = Mixer()
    for song, source in enumerate(sources):
        print(f"[{song + 1}/{len(sources)}] loading {source}")
        try:
            track = load_source(source)
        except Exception as exc:
            sys.exit(f"Could not load {source}\n{exc}")
        track.cues = load_cues(track.track_id)
        mixer.set_track(song, track)

    mixer.start()
    try:
        SamplerApp(mixer).run()
    finally:
        mixer.stop()


if __name__ == "__main__":
    main()
