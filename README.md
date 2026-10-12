# PySamp (test version 0.2)

A terminal sampler/mixer. You load up to 8 songs. Each row of your computer keyboard is one song. You mark your own cue points in each song. Then each key in the row jumps to one of your cue points and plays from there.

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

## The 3 steps

### Step 1: load songs

Start PySamp. It asks for songs:

```
Song 1: <paste a YouTube link, or drag in an audio file>
Song 2: <another one>
```

- Paste up to 8. Press Enter on an empty line when you are done.
- A song can be a YouTube link or the path to a file on your computer (wav, flac, ogg, mp3).
- You can also pass them on the command line: `PySamp SOURCE1 SOURCE2 ...`
- YouTube songs are downloaded and converted. A 4-minute song takes a few seconds.
- Songs 1-4 are **bank A**. Songs 5-8 are **bank B**.

Downloads are saved in `~/PySamp/downloads` (Windows: `C:\Users\<you>\PySamp\downloads`). A song you loaded before is reused.

### Step 2: mark cue points (Edit mode)

PySamp starts in **Edit mode**.

1. Pick a song with `Up` / `Down`.
2. Press `Space` to play. Press `Space` again to pause.
3. Press `m` at each moment you want a cue (a drop, a beat, a vocal).
4. Use `Left` / `Right` to jump back or ahead 5 seconds if you missed it.

Cues fill the keys in order: the first `m` is key 1, the second is key 2, and so on up to key 0 (the 10th). The 11th to 20th go on **page 2** (see below). Each song holds up to 20 cues.

Your cues are saved automatically in `~/PySamp/cues`. Next time you load the same song, they are back.

Made a mistake? `Backspace` deletes the last cue.

### Step 3: perform (Play mode)

Press `Enter` to switch to **Play mode**. Now each key in the row jumps to a cue and plays. Press `Enter` again to go back to Edit mode.

## Controls

### Row keys

Each row is one song. Each key in the row is one cue (left to right).

| Row | Keys | Song in bank A | Song in bank B |
|-----|------|----------------|----------------|
| 1 (number row) | `1 2 3 4 5 6 7 8 9 0` | Song 1 | Song 5 |
| 2 | `Q W E R T Y U I O P` | Song 2 | Song 6 |
| 3 | `A S D F G H J K L ;` | Song 3 | Song 7 |
| 4 | `Z X C V B N M , . /` | Song 4 | Song 8 |

### Bank and page keys (work in both modes)

| Key | Action |
|-----|--------|
| `Tab` | Switch bank: songs 1-4 (A) or songs 5-8 (B) |
| `` ` `` (backtick, left of `1`) | Switch cue page: cues 1-10 (page 1) or cues 11-20 (page 2) |
| `Up` / `Down` | Select the previous / next song (moves between banks) |
| `Enter` | Switch between Edit mode and Play mode |
| `Ctrl+Q` | Quit |

Both together give all 4 combinations:

| Bank | Page | Songs | Cues |
|------|------|-------|------|
| A | 1 | 1-4 | 1-10 |
| A | 2 | 1-4 | 11-20 |
| B | 1 | 5-8 | 1-10 |
| B | 2 | 5-8 | 11-20 |

The top line of the screen always shows the active mode, bank, and page.

### Edit mode keys

| Key | Action |
|-----|--------|
| `Space` | Play / pause the selected song |
| `m` | Mark a cue at the current position |
| `Left` / `Right` | Jump back / ahead 5 seconds |
| `Backspace` | Delete the last cue |
| Row keys | Audition a saved cue (except `m`, which marks) |

### Play mode keys

| Key | Action |
|-----|--------|
| Row keys | Jump to that cue and play |
| `Left` / `Right` | Volume down / up for the selected song (5% per press) |
| `Space` | Stop all songs |

Pressing a row key also selects that song, so `Left` / `Right` right after a trigger changes the volume of the song you just hit.

## The screen

```
PLAY MODE  |  bank A: songs 1-4  |  page 1: cues 1-10
>  1..0  Song title here      vol [##########]  cues  4/20  last 3  1:12/3:45
    |....:...|.....>.........|.........|......
   q..p  (empty)
```

- `>` at the far left marks the selected song.
- `1..0` is the key range of that row.
- `cues 4/20` is how many cues the song has.
- `last 3` is the last key you triggered on the current page.
- The bar is the song. `|` is a cue on the current page. `:` is a cue on the other page. `>` is the playhead while playing. `o` is the playhead when stopped.

## Known limits

- Cues fill in the order you mark them. They are not sorted by time.
- You can only delete the last cue, not one in the middle.
- Songs load at start. To change songs, quit and start again.
- Terminals cannot see a key being held or released, and cannot see Command or Option. So bank and page are toggle keys (`Tab`, `` ` ``), not hold keys. There is no "hold to play".
- No loop, mute, solo, tempo, pitch, or EQ.
- Volume is per song only. The master level is your system volume.
- Many keyboards cannot read more than about 6 keys at once.

## Troubleshooting

- **No sound:** check your system output device. Check that the volume of the song is above zero (`Right` raises it in Play mode). In Edit mode, press `Space` on the selected song.
- **Key does nothing:** that cue is not marked yet. Check the page (`` ` ``) and bank (`Tab`) in the top line.
- **Download fails:** check the link opens in a browser. YouTube changes often, so a new download may fail until the app is updated. Songs already in the downloads folder still work.
- **Mac says the app "cannot be opened":** run the `xattr` command in the Install section.
- **Screen looks broken:** make the terminal window larger (at least 100 columns wide).

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

The zip appears in `dist/`. The GitHub Actions workflow (`.github/workflows/build.yml`) builds both Mac and Windows packages when you push a tag like `v0.2.0`.

## Feedback wanted

For the DJ test, please answer:

1. Is marking cues with `m` fast enough? Do you miss the beat? Would you want to nudge a cue after marking?
2. Do `Tab` (bank) and `` ` `` (page) feel natural while playing? Would you prefer other keys?
3. Is 20 cues per song enough? Is 8 songs enough?
4. Do you need cues sorted by time, or labeled?
5. What is missing to use it live? (loop, tempo match, key-lock, EQ, mute/solo, crossfade, hold-to-play, master volume, loading songs without restarting)
6. Is there delay between key press and sound?
7. Did the install work first try? Where did you get stuck?
8. Any crashes? Send the text on the screen and the link you used.

## Note

Downloading audio from YouTube may break YouTube's terms and copyright rules. Use this for personal testing only.
