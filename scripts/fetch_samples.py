"""Download the instrument samples bundled in pysamp/samples.

Source: FluidR3_GM, as published by https://github.com/gleitz/midi-js-soundfonts
(Creative Commons Attribution 3.0). The ogg bytes are copied as they are, one
file per note, every third semitone; PySamp pitch-shifts in between.
"""
import base64
import re
import ssl
import sys
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pysamp.instruments import INSTRUMENTS, SAMPLES_DIR, note_name, sample_notes  # noqa: E402

URL = "https://gleitz.github.io/midi-js-soundfonts/FluidR3_GM/{}-ogg.js"
GM_NAMES = {
    "piano": "acoustic_grand_piano",
    "epiano": "electric_piano_1",
    "organ": "drawbar_organ",
    "strings": "string_ensemble_1",
    "guitar": "acoustic_guitar_nylon",
    "bass": "electric_bass_finger",
    "choir": "choir_aahs",
    "lead": "lead_2_sawtooth",
    "brass": "brass_section",
}


def main() -> None:
    context = ssl.create_default_context(cafile=certifi.where())
    for instrument in INSTRUMENTS:
        url = URL.format(GM_NAMES[instrument.id])
        text = urllib.request.urlopen(url, timeout=120, context=context).read().decode()
        found = dict(re.findall(r'"([A-G][b#]?\d)": "data:audio/ogg;base64,([^"]+)"', text))
        folder = SAMPLES_DIR / instrument.id
        folder.mkdir(parents=True, exist_ok=True)
        for midi in sample_notes(instrument):
            name = note_name(midi)
            (folder / f"{name}.ogg").write_bytes(base64.b64decode(found[name]))
        print(instrument.id, len(list(folder.glob("*.ogg"))), "notes")


if __name__ == "__main__":
    main()
