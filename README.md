# PySamp (test version)

A terminal sampler/mixer. You load up to 4 songs from YouTube. Each row of your computer keyboard is one song. Each key in that row jumps to a different spot in that song and plays from there.

This is an early test build. Please break it and send feedback (questions at the bottom).

## Install

### Mac (Apple Silicon: M1/M2/M3/M4)

1. Download `PySamp-mac-arm64.zip` from the Releases page and unzip it.
2. Open Terminal and remove the download block that macOS puts on unsigned apps:
   ```
   xattr -dr com.apple.quarantine ~/Downloads/PySamp
   ```
   (Change the path if you unzipped somewhere else.)
3. Start it:
   ```
   ~/Downloads/PySamp/PySamp
   ```

Intel Macs: not packaged. Use "Run from source" below.

### Windows

1. Download `PySamp-windows-amd64.zip` from the Releases page and unzip it.
2. Open the `PySamp` folder and double-click `PySamp.exe`.
3. If SmartScreen says "Windows protected your PC", click **More info**, then **Run anyway**. The app is not code-signed.

Use Windows Terminal if you have it. The classic console window also works, but looks worse.

## Start a session

1. Start PySamp. It asks for links:
   ```
   Song 1 link: <paste a YouTube link>
   Song 2 link: <paste another>
   ```
   Paste up to 4. Press Enter on an empty line when you are done.
   You can also pass links on the command line: `PySamp URL1 URL2 URL3 URL4`.
2. PySamp downloads each song as audio and converts it. A 4-minute song takes a few seconds.
3. The mixer screen opens and you can play right away.

Songs are saved in `~/PySamp/downloads` (on Windows: `C:\Users\<you>\PySamp\downloads`). A song you loaded before is reused and not downloaded again.

## The screen

```
>  1..0  Song title here                vol [##########]  cue 3
    |.........|.........>.........|.........|......
   q..p  (empty)
```

- `>` at the far left marks the selected row.
- `1..0` is the key range of that row.
- `vol` is the row volume (10 steps).
- `cue` is the last key you pressed in that row.
- The bar under the title is the song. `|` marks a cue point. `>` is the playhead while playing. `o` is the playhead when stopped.

## Controls

### Row keys (play)

Each row is one song. Each key in the row is one cue point.

| Row | Keys (left to right = cue 1 to 10) | Song |
|-----|------------------------------------|------|
| 1 (number row) | `1 2 3 4 5 6 7 8 9 0` | Song 1 |
| 2 | `Q W E R T Y U I O P` | Song 2 |
| 3 | `A S D F G H J K L ;` | Song 3 |
| 4 | `Z X C V B N M , . /` | Song 4 |

- Press a key: the song jumps to that cue and plays from there.
- Press the same key again: it restarts from that cue.
- Songs in different rows play at the same time and are mixed together.
- Each row plays one spot at a time. Pressing a new key in a row replaces the old spot.
- Pressing a key in an empty row does nothing.

### Cue points

Each song is cut into 10 equal parts. Cue 1 is the start. Cue 2 is 10% in. Cue 3 is 20% in. Cue 10 (the last key in the row) is 90% in. A 4-minute song gives a cue every 24 seconds.

### Mixer keys

| Key | Action |
|-----|--------|
| `Up` / `Down` | Select the previous / next row |
| `Left` / `Right` | Volume down / up for the selected row (5% per press) |
| `Space` | Stop all rows |
| `Ctrl+Q` | Quit |

Pressing a row key also selects that row. So `Right`/`Left` right after a trigger changes the volume of the song you just hit.

## Known limits (v1)

- Cue points are equal slices. You cannot set your own cue points yet.
- No loop, mute, solo, tempo, pitch, or EQ.
- A terminal reports key presses only, not key releases. So there is no "hold to play".
- Volume is per row only. The master level is your system volume.
- Maximum 4 songs.
- Many keyboards cannot read more than about 6 keys at once.

## Troubleshooting

- **No sound:** check your system output device. Check that the volume of the row is above zero (`Right` raises it).
- **Download fails:** check the link opens in a browser. YouTube changes often, so a new download may fail until the app is updated. Songs already in the downloads folder still work.
- **Mac says the app "cannot be opened":** run the `xattr` command in the Install section.
- **Screen looks broken:** make the terminal window larger (at least 80 columns wide).

## Run from source (Intel Mac, Linux, or to change the code)

Needs Python 3.10 or newer.

```
git clone https://github.com/osagafuichi/PySamp
cd PySamp
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pysamp
```

On Windows use `.venv\Scripts\pip` and `.venv\Scripts\pysamp`.

Run the tests:

```
cd tests
../.venv/bin/python test_engine.py
../.venv/bin/python test_app.py
```

## Build the packages

Run on the OS you want to package for:

```
.venv/bin/pip install -e ".[build]"
.venv/bin/python scripts/build.py
```

The zip appears in `dist/`. The GitHub Actions workflow (`.github/workflows/build.yml`) builds both Mac and Windows packages when you push a tag like `v0.1.0`.

## Feedback wanted

For the DJ test, please answer:

1. Does the key layout feel right for playing? Which row feels best or worst?
2. Is 10 equal cue points useful, or do you need to set your own (for example on beats or drops)?
3. What is missing to use it live? (loop, tempo match, key-lock, EQ, mute/solo, crossfade, hold-to-play, master volume)
4. Is there delay between key press and sound?
5. Did the install work first try? Where did you get stuck?
6. Any crashes? Send the text on the screen and the link you used.

## Note

Downloading audio from YouTube may break YouTube's terms and copyright rules. Use this for personal testing only.
