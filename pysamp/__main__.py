import sys
from pathlib import Path

from pysamp.app import SamplerApp
from pysamp.downloader import download
from pysamp.engine import NUM_ROWS, Mixer, load_track

DOWNLOAD_DIR = Path("downloads")


def main() -> None:
    urls = sys.argv[1:]
    if not urls or len(urls) > NUM_ROWS:
        sys.exit(f"usage: python -m pysamp URL [URL ...]  (1-{NUM_ROWS} URLs, one per keyboard row)")

    mixer = Mixer()
    for row, url in enumerate(urls):
        print(f"[{row + 1}/{len(urls)}] fetching {url}")
        path, title = download(url, DOWNLOAD_DIR)
        mixer.set_track(row, load_track(path, title))

    mixer.start()
    try:
        SamplerApp(mixer).run()
    finally:
        mixer.stop()


if __name__ == "__main__":
    main()
