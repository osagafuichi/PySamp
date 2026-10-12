# PySamp (test version 0.4)

A sampler/mixer that runs in your browser. You load up to 8 songs. Each row of your computer keyboard is one song. You mark your own cue points in each song. Then each key in the row jumps to one of your cue points and plays from there. The page shows each song as a waveform with your cue points on it.

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
   Your browser opens with PySamp. If it does not, copy the `http://127.0.0.1:...` address printed in Terminal into your browser.

Intel Macs: not packaged. Use "Run from source" below.

### Windows

1. Download `PySamp-windows-amd64.zip` from the Releases page and unzip it.
2. Open the `PySamp` folder and double-click `PySamp.exe`.
3. If SmartScreen says "Windows protected your PC", click **More info**, then **Run anyway**. The app is not code-signed.
4. A black console window opens and your browser opens with PySamp. Keep the console window open while you use PySamp.

PySamp only talks to your own computer (`127.0.0.1`). Nothing is exposed to the network. Each start makes a new address with a secret code, so an old bookmark will not work.

## The 3 steps

### Step 1: load songs

Each of the 4 song panels has a text box at the bottom. Paste a YouTube link or a file path and press `Enter` (or click **Load**).

- A song can be a YouTube link or the path to a file on your computer (wav, flac, ogg, mp3).
- YouTube songs are downloaded and converted. A 4-minute song takes a few seconds. The status line under the songs shows `Loading...` and then `Loaded song N`. The app keeps working meanwhile.
- You can load into any slot, in any order. Loading into a slot that already has a song replaces it. The old song's cues stay saved on disk.
- Songs 1-4 are **bank A**. Songs 5-8 are **bank B**. Use the bank buttons or `Tab` to see the other four.
- You can also preload songs from the command line: `PySamp SOURCE1 SOURCE2 ...`

Downloads are saved in `~/PySamp/downloads` (Windows: `C:\Users\<you>\PySamp\downloads`). A song you loaded before is reused.

### Step 2: mark cue points (Edit mode)

PySamp starts in **Edit mode**.

1. Pick a song with its selector key (`1`, `Q`, `A`, or `Z`), by clicking its panel, or with `Up` / `Down`.
2. Press `Space` to play. Press `Space` again to pause.
3. Press `M` at each moment you want a cue (a drop, a beat, a vocal).
4. Use `Left` / `Right` to jump back or ahead 5 seconds, or press on the waveform and drag to move the playhead.

Cues fill the cue keys of the song's row in order. On row 1 the first `M` is key `2`, the second is `3`, and so on up to `0` (the 9th). The 10th to 18th go on **page 2** (see below). Each song holds up to 18 cues. Each cue shows on the waveform as an orange flag with its key letter. The status line tells you which cue you just marked.

Your cues are saved automatically in `~/PySamp/cues`. Next time you load the same song, they are back.

Made a mistake? Hold a cue key and press `Backspace` to delete that one cue. The cues that remain are then renumbered by their position in the song, earliest first, so there are no gaps. `Backspace` alone deletes the last cue you marked.

### Step 3: perform (Play mode)

Press `Enter` (or click the mode button) to switch to **Play mode**. Now each cue key in a row jumps to a cue and plays. Press `Enter` again to go back to Edit mode.

## Controls

The page must be the active browser tab, and the cursor must not be in a text box, for keys to work. Press `Esc` to leave a text box.

### Row keys

Each row is one song. The **first key** of the row selects that song. The other **nine keys** are its cues (left to right).

| Row | Select song | Cue keys (cues 1-9 on page 1) | Song in bank A | Song in bank B |
|-----|-------------|-------------------------------|----------------|----------------|
| 1 (number row) | `1` | `2 3 4 5 6 7 8 9 0` | Song 1 | Song 5 |
| 2 | `Q` | `W E R T Y U I O P` | Song 2 | Song 6 |
| 3 | `A` | `S D F G H J K L ;` | Song 3 | Song 7 |
| 4 | `Z` | `X C V B N M , . /` | Song 4 | Song 8 |

A selector key only selects. It never plays. The selected song has the teal border and is the one the scroll wheel controls. Keys follow the physical key positions, so other keyboard layouts work the same way.

### Mouse and trackpad

| Action | Result |
|--------|--------|
| Scroll anywhere in the window | Volume of the **selected song** (no need to hover) |
| Click a song panel | Select that song |
| Click an orange cue flag | Jump to that cue and play |
| Press and drag on the waveform (Edit mode) | Move the playhead. It follows the pointer, also while playing |
| Hold right button and scroll | Pitch of the **selected song** |
| Hold `Option` (Mac) or `Alt` (Windows) and scroll | Pitch of the selected song (use this on a trackpad) |
| Click the pitch bar of a song | Reset its pitch to normal |
| Mode / bank / page buttons | Same as `Enter` / `Tab` / `` ` `` |

- Mouse wheel and two-finger trackpad scrolling both work. A bigger scroll changes the volume more.
- Pitch works like a turntable: higher pitch also means faster tempo. The range is half speed to double speed. Pitch is not saved. It resets when you restart.
- On a Mac trackpad, "hold right-click and scroll" needs one finger pressed in a two-finger click while another finger scrolls. That is hard, so use `Option` + scroll instead.
- The direction follows your system "natural scrolling" setting. If it feels backwards, flip that setting.
- A fast trackpad flick keeps scrolling for a moment (momentum), so use small movements for fine control.

### Bank and page keys (work in both modes)

| Key | Action |
|-----|--------|
| `Tab` | Switch bank: songs 1-4 (A) or songs 5-8 (B) |
| `` ` `` (backtick, left of `1`) | Switch cue page: cues 1-9 (page 1) or cues 10-18 (page 2) |
| `Up` / `Down` | Select the previous / next song (moves between banks) |
| `Enter` | Switch between Edit mode and Play mode |

Both together give all 4 combinations:

| Bank | Page | Songs | Cues |
|------|------|-------|------|
| A | 1 | 1-4 | 1-9 |
| A | 2 | 1-4 | 10-18 |
| B | 1 | 5-8 | 1-9 |
| B | 2 | 5-8 | 10-18 |

### Edit mode keys

| Key | Action |
|-----|--------|
| `Space` | Play / pause the selected song |
| `M` | Mark a cue at the current position |
| `Left` / `Right` | Jump back / ahead 5 seconds |
| Hold a cue key + `Backspace` | Delete that cue. The rest are renumbered by position in the song |
| `Backspace` alone | Delete the last cue |
| Cue keys | Audition a saved cue (except `M`, which marks) |

### Play mode keys

| Key | Action |
|-----|--------|
| Cue keys | Jump to that cue and play |
| `Left` / `Right` | Volume down / up for the selected song (5% per press) |
| `Space` | Stop all songs |

Pressing a cue key also selects that song, so scrolling or `Left` / `Right` right after a trigger changes the volume of the song you just hit.

## The screen

- **Top bar:** the mode, bank, and page buttons (the active ones are teal) and **Quit**.
- **One panel per song** in the current bank:
  - The badge on the left is the selector key. The title line shows the song number and name.
  - On the right: current time / length, how many cues are set (`5/18`), and `playing` or `stopped`.
  - The waveform: teal is already played, grey is still to come. The white line is the playhead.
  - Orange flags are the cues on the current page, each with its key letter. The white flag is the last cue you triggered. Faint lines are cues on the other page.
  - The bar at the bottom left is the volume. Next to it is the pitch bar: the tick in the middle is normal pitch, the fill grows left (slower) or right (faster), and the number shows the change in percent. The text box loads a song into this slot.
- **Status line:** what just happened (cue marked, song loaded, errors).
- **Help line:** the keys for the current mode.

## Quit

Click **Quit** in the page, or press `Ctrl+C` in the console window. Closing the browser tab does **not** stop PySamp, and sound keeps playing.

## Known limits

- Cues fill in the order you mark them. They are sorted by time only when you delete one. After that, a new cue goes into the first free slot, which can be out of time order. Flags that are close together can overlap.
- You cannot delete with `M` held, because `M` marks a cue in Edit mode. Delete is Edit mode only.
- You cannot remove a song from a slot. You can only replace it with another song.
- Bank and page are toggle keys (`Tab`, `` ` ``), not hold keys. There is no "hold to play" yet. Command is not usable because the browser keeps those shortcuts.
- In Edit mode `M` marks a cue, so cue 5 of row 4 (the `M` key) cannot be auditioned there. It works in Play mode.
- No loop, mute, solo, tempo-only change, key lock, or EQ. Pitch and tempo change together.
- Sound at high pitch settings may be a little rough (simple resampling).
- Volume is per song only. The master level is your system volume.
- Many keyboards cannot read more than about 6 keys at once.

## Troubleshooting

- **No sound:** check your system output device. Check that the volume of the song is above zero (scroll up raises it). In Edit mode, press `Space` on the selected song.
- **Browser did not open:** copy the `http://127.0.0.1:...` address from the console window into your browser.
- **"PySamp is not running" banner:** the app was quit or crashed. Start it again and use the new address.
- **Keys do nothing:** click on the page background first (the cursor may be in a text box, or another tab is active). Check that a song is loaded in that slot and the cue is marked. Check the page (`` ` ``) and bank (`Tab`).
- **Scroll changes the wrong song:** scroll changes the **selected** song only (teal border). Select the song first.
- **"Could not load song N":** the status line shows the reason. A wrong link or a missing file are the usual causes. The slot stays as it was.
- **"YouTube blocked the download (bot check)":** YouTube sometimes asks for a login. PySamp then tries the cookies of your browser (Chrome, Safari, Firefox, Edge, Brave), so log in to YouTube in one of them first. On Mac, allow the Keychain prompt for Chrome, or give Terminal "Full Disk Access" for Safari. To force one browser, start with `PYSAMP_BROWSER=firefox`. A local audio file always works.
- **Download fails:** check the link opens in a browser. YouTube changes often, so a new download may fail until the app is updated. Songs already in the downloads folder still work.
- **Mac says the app "cannot be opened":** run the `xattr` command in the Install section.
- **Waveform stays on "Drawing waveform...":** reload the page. If it repeats, send the text from the console window.

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
../.venv/bin/python test_server.py
../.venv/bin/python test_downloader.py
```

## Build the packages

Run on the OS you want to package for:

```
.venv/bin/pip install -e ".[build]"
.venv/bin/python scripts/build.py
```

The zip appears in `dist/`. The GitHub Actions workflow (`.github/workflows/build.yml`) builds both Mac and Windows packages when you push a tag like `v0.4.0`.

## Feedback wanted

For the DJ test, please answer:

1. Is the page clear at a glance? Can you tell which song is selected, where the cues are, and what mode you are in?
2. Is marking cues with `M` fast enough? Do you miss the beat? Would you want to nudge a cue after marking?
3. Do `Tab` (bank) and `` ` `` (page) feel natural while playing? Would you prefer other keys?
4. Is 18 cues per song enough? Is 8 songs enough? Is it a problem that the first key of each row is a selector and not a cue?
5. Does scroll-for-volume feel good (step size, trackpad momentum, direction)?
6. What is missing to use it live? (loop, tempo match, key-lock, EQ, mute/solo, crossfade, hold-to-play, master volume, removing a song)
   Does pitch feel right (step size, range)? Do you need pitch to change tempo only, without changing the key (key-lock)?
7. Is there delay between key press and sound?
8. Did the install work first try? Where did you get stuck?
9. Any crashes? Send the text from the console window and the link you used.

## Note

Downloading audio from YouTube may break YouTube's terms and copyright rules. Use this for personal testing only.
