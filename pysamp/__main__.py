import sys
from pathlib import Path

from pysamp.app import SamplerApp
from pysamp.downloader import download
from pysamp.engine import NUM_ROWS, Mixer, load_track

DOWNLOAD_DIR = Path.home() / "PySamp" / "downloads"


def prompt_for_urls() -> list[str]:
    print(f"PySamp: paste up to {NUM_ROWS} YouTube links, one per keyboard row.")
    print("Press Enter on an empty line when done.\n")
    urls: list[str] = []
    while len(urls) < NUM_ROWS:
        url = input(f"Song {len(urls) + 1} link: ").strip()
        if not url:
            break
        urls.append(url)
    return urls


def main() -> None:
    urls = sys.argv[1:] or prompt_for_urls()
    if not urls or len(urls) > NUM_ROWS:
        sys.exit(f"Need 1-{NUM_ROWS} links. Usage: pysamp URL [URL ...]")

    mixer = Mixer()
    for row, url in enumerate(urls):
        print(f"[{row + 1}/{len(urls)}] downloading {url}")
        try:
            path, title = download(url, DOWNLOAD_DIR)
        except Exception as exc:
            sys.exit(f"Could not download {url}\n{exc}")
        mixer.set_track(row, load_track(path, title))

    mixer.start()
    try:
        SamplerApp(mixer).run()
    finally:
        mixer.stop()


if __name__ == "__main__":
    main()
