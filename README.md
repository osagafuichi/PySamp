# PySamp 1.0

A sampler for your browser. Load songs, mark your favourite moments as **cue points**, then jump to them with your keyboard. Turn on Caps Lock to play instruments and drums, and to record what you play.

- Up to **8 songs**. Each keyboard row is one song.
- Up to **18 cue points** per song. Each cue is one key.
- **Caps Lock** turns the keyboard into a piano or a drum kit.
- **Record** your whole performance and play the recordings back.

## Install

### Mac (Apple Silicon: M1 to M4)

1. Download `PySamp-mac-arm64.zip` from the Releases page. Unzip it.
2. Open Terminal. Remove the block macOS puts on unsigned apps:
   ```
   xattr -dr com.apple.quarantine ~/Downloads/PySamp
   ```
3. Start it:
   ```
   ~/Downloads/PySamp/PySamp
   ```

Your browser opens with PySamp. If not, copy the `http://127.0.0.1:...` address from Terminal into your browser. Intel Mac: use [Run from source](#run-from-source).

### Windows

1. Download `PySamp-windows-amd64.zip` from the Releases page. Unzip it.
2. Double-click `PySamp.exe` in the `PySamp` folder.
3. If Windows says "protected your PC", click **More info**, then **Run anyway**. The app is not code-signed.
4. A console window opens, and then your browser. Keep the console window open.

PySamp only talks to your own computer (`127.0.0.1`). Nothing goes on the network. Each start makes a new secret address, so old bookmarks stop working.

## Quick start

### 1. Load songs

Each song panel has a text box. Paste a **YouTube link** or a **file path** (wav, flac, ogg, mp3). Press `Enter`.

- Songs 1 to 4 are **bank A**. Songs 5 to 8 are **bank B**. Press `Tab` to switch.
- YouTube songs are downloaded to `~/PySamp/downloads` and reused next time.
- You can also load from the command line: `PySamp SONG1 SONG2 ...`

### 2. Mark cues (Edit mode)

PySamp starts in **Edit mode**.

1. Select a song: press its first key (`1`, `Q`, `A` or `Z`), or click it.
2. Press `Space` to play. Press `M` at every moment you want a cue.
3. `Left` / `Right` jump 5 seconds. You can also drag on the waveform.

Cues are saved in `~/PySamp/cues`. They come back when you load the same song again.

### 3. Perform (Play mode)

Press `Enter` to switch to **Play mode**. Now each cue key jumps to its cue and plays. Press `Enter` again to go back.

## Key cheat sheet

Each row is one song. The **first key** selects the song. The **other nine keys** are its cues.

| Row | Select | Cue keys | Bank A | Bank B |
|-----|--------|----------|--------|--------|
| 1 | `1` | `2 3 4 5 6 7 8 9 0` | Song 1 | Song 5 |
| 2 | `Q` | `W E R T Y U I O P` | Song 2 | Song 6 |
| 3 | `A` | `S D F G H J K L ;` | Song 3 | Song 7 |
| 4 | `Z` | `X C V B N M , . /` | Song 4 | Song 8 |

### Always

| Key | Action |
|-----|--------|
| `Tab` | Switch bank (A / B) |
| `` ` `` | Switch cue page (cues 1-9 / cues 10-18) |
| `Up` / `Down` | Select previous / next song |
| `Enter` | Switch Edit mode / Play mode |
| `\` | Start / stop recording |
| `Caps Lock` | Instruments and drums on / off |
| Scroll | Volume of the selected song |
| `Option` (Mac) or `Alt` + scroll | Pitch of the selected song |

`Tab` and `` ` `` work two ways. **Tap** them and the new bank or page stays. **Hold** them and it only lasts while you hold. Use a hold to fire one cue from the other bank or page.

### Edit mode

| Key | Action |
|-----|--------|
| `Space` | Play / pause the selected song |
| `M` | Mark a cue here |
| `Left` / `Right` | Jump back / ahead 5 seconds |
| Cue key | Listen to that cue |
| Hold a cue key + `Backspace` | Delete that cue |
| `Backspace` | Delete the last cue |

### Play mode

| Key | Action |
|-----|--------|
| Cue key | Jump to the cue and play. **Other songs stop** |
| `Shift` + cue key | Play the cue and **keep the other songs playing** |
| `Left` / `Right` | Volume down / up (selected song) |
| `Space` | Stop everything |

`Shift` also layers inside one song. If the song is already playing, the new cue starts on top of it (up to 8 at once).

### Caps Lock: piano

Turn Caps Lock on. Press `1` to `9` to pick an instrument.

| Key | Instrument |
|-----|------------|
| `1` Grand Piano | `2` Electric Piano |
| `3` Organ | `4` Strings |
| `5` Guitar | `6` Bass |
| `7` Choir | `8` Synth Lead |
| `9` Brass | `0` Drum kit |

The keys are laid out like a real piano:

```
 black keys:      W  E     T  Y  U     O  P
 white keys:     A  S  D  F  G  H  J  K  L  ;  '
 notes:          C  D  E  F  G  A  B  C  D  E  F
```

| Key | Action |
|-----|--------|
| `Z` / `X` | Octave down / up |
| `C` / `V` | Softer / louder (10% steps, starts at 80%) |

Hold a key to sustain the note. Hold several keys for a chord. The screen shows the note names on the keys.

### Caps Lock: drums

Press `0` for the drum kit. Each key is one drum pad. The screen shows the pad names.

| Row | Keys | Sounds |
|-----|------|--------|
| Top | `Q W E R T Y U I O P` | hi-hats, shaker, ride, crashes |
| Home | `A S D F G H J K L ;` | snares, claps, rim, snap |
| Bottom | `Z X C V B N M , . /` | kicks and toms |

The four hi-hats cut each other off, like a real kit.

## Recording

Press `\` (or click **Record**) to start. The button turns red and shows the time. Press `\` again to stop.

- It records **what PySamp plays**: songs, drums, notes and takes, with your volume and pitch moves. It does not record your microphone or other apps.
- Files are WAV (stereo, 44.1 kHz) in `~/PySamp/recordings`. An old file is never overwritten. The status line shows the path.

### Recordings screen

If **Caps Lock is on** while you record, the screen changes:

```
+----------------------------------------+
|  Songs (top half)                      |
+--------------------+-------------------+
|  Keyboard          |  Recording lane 1 |
|  (piano or drums)  |  Recording lane 2 |
|                    |  Recording lane 3 |
+--------------------+-------------------+
```

- While you record, a red lane shows how loud it is.
- When you stop, the recording becomes a **take**: a lane with its waveform. New takes go **below** the old ones. The list holds 8 takes.
- **Play** / **Stop** plays a take. Click the waveform to start from that point. Several takes can play together, and you can play the keyboard over them.
- **Use as song** loads the take into the selected song slot. Then you can mark cues in it like any song.
- **x** removes a take from the list. The WAV file stays on disk.
- Record while takes play to layer them: the new recording contains them.
- Turn Caps Lock off to see the normal screen. Takes stay in memory until you quit.

## The screen

- **Top bar:** mode, bank, page, **Record**, **Quit**. The active buttons are teal.
- **Song panel:** badge (selector key), title, time, cue count, `playing` or `stopped`. In the waveform, teal is played, grey is still to come, the white line is the playhead. Orange flags are cues on this page. Below it: volume bar, pitch bar (click it to reset), and the load box.
- **Status line:** what just happened. **Help line:** the keys for the current mode.

You can also use the mouse: click a song to select it, click an orange flag to play that cue, drag on the waveform (Edit mode) to move the playhead, and click the mode, bank and page buttons.

## Quit

Click **Quit**, or press `Ctrl+C` in the console. Closing the browser tab does **not** stop PySamp.

## Known limits

- You cannot remove a song from a slot. You can only replace it.
- In Edit mode `M` marks a cue, so the `M` cue key (row 4) only plays in Play mode.
- Cues are sorted by time only when you delete one. After that, a new cue can land out of time order.
- No loop, mute, solo, EQ or key lock. Pitch and speed change together (half speed to double). Pitch is not saved.
- Volume is per song. Drums and notes are not affected by it. The master level is your system volume.
- Instruments are played from small sample sets, so some notes sound less natural. Piano, Electric Piano, Guitar and Bass fade out by themselves after a few seconds.
- Drums are made by the program and are not adjustable.
- The first note after you pick a new instrument can be a little late. Pressing its number key loads it ahead of time.
- Keys go through the browser, so there can be a few milliseconds of delay.
- Many keyboards cannot read more than about 6 keys at once.
- A recording saves audio only, not your key presses. There is no pause or trim.
- Takes are not kept after you quit. Their WAV files are.
- On some computers the Caps Lock state shows only after you press a key or move the mouse.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No sound | Check your output device. Raise the song volume (scroll up). In Edit mode press `Space`. |
| Browser did not open | Copy the `http://127.0.0.1:...` address from the console. |
| "PySamp is not running" | The app quit. Start it again and use the new address. |
| Keys do nothing | Click the page background (the cursor may be in a text box). Check the song is loaded, the cue is marked, and the bank (`Tab`) and page (`` ` ``) are right. |
| Scroll changes the wrong song | Scroll changes the selected song (teal border). Select it first. |
| "Could not load song N" | The status line gives the reason (bad link, missing file). The slot stays as it was. |
| "YouTube blocked the download" | Log in to YouTube in Chrome, Safari, Firefox, Edge or Brave. PySamp uses that browser's cookies. On Mac, allow the Keychain prompt. To pick a browser: `PYSAMP_BROWSER=firefox`. A local file always works. |
| Download fails | Check the link opens in a browser. YouTube changes often, so you may need a newer PySamp. Downloaded songs still work. |
| Mac says the app "cannot be opened" | Run the `xattr` command from the Install section. |
| Waveform stays on "Drawing waveform..." | Reload the page. |

## Run from source

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
../.venv/bin/python test_instruments.py
../.venv/bin/python test_drums.py
../.venv/bin/python test_downloader.py
```

### Build the packages

Run on the OS you want to package for:

```
.venv/bin/pip install -e ".[build]"
.venv/bin/python scripts/build.py
```

The zip appears in `dist/`. GitHub Actions builds the Mac and Windows zips and attaches them to a release when you push a tag like `v1.0.0`.

## Credits

The instrument sounds come from the FluidR3_GM soundfont, as packaged in the gleitz/midi-js-soundfonts project, under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). They are stored inside the app (about 3.7 MB). `scripts/fetch_samples.py` downloads them again. The drum sounds are synthesized by the program.

## Feedback wanted

1. Is the page clear at a glance? Can you tell the selected song, the cues and the mode?
2. Is marking cues with `M` fast enough?
3. Do `Tab` and `` ` `` feel natural? Is 18 cues and 8 songs enough?
4. Is it right that a cue key stops the other songs unless you hold `Shift`?
5. What is missing to use it live? (loop, tempo match, key lock, EQ, mute/solo, crossfade, master volume)
6. Is there a delay between key press and sound, especially for drums?
7. Do the drums and instruments sound good enough? What is missing?
8. Is the piano layout easy to learn? Does the recordings screen work for you? What should a take be able to do?
9. Does recording the audio fit your needs, or do you want to record key presses so you can edit them?
10. Did the install work first try? Any crashes? Send the console text.

## Note

Downloading audio from YouTube may break YouTube's terms and copyright rules. Use PySamp for personal testing only.
