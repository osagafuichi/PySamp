import sys
import threading
import webbrowser

from pysamp.engine import NUM_SONGS, Mixer
from pysamp.loader import load_source
from pysamp.server import SamplerServer


def main() -> None:
    sources = sys.argv[1:]
    if len(sources) > NUM_SONGS:
        sys.exit(f"Too many songs. Maximum is {NUM_SONGS}. Usage: pysamp [SOURCE ...]")

    mixer = Mixer()
    for song, source in enumerate(sources):
        print(f"[{song + 1}/{len(sources)}] loading {source}")
        try:
            mixer.set_track(song, load_source(source))
        except Exception as exc:
            sys.exit(f"Could not load {source}\n{exc}")

    server = SamplerServer(mixer)
    mixer.start()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"PySamp is running at {server.url}")
    print("Click Quit in the page, or press Ctrl+C here, to stop.", flush=True)
    webbrowser.open(server.url)
    try:
        while not server.quit_event.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        mixer.stop()


if __name__ == "__main__":
    main()
