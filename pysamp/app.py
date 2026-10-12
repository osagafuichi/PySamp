from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import Key
from textual.widgets import Static

from pysamp.cuestore import save_cues
from pysamp.engine import (
    CUES_PER_PAGE,
    NUM_PAGES,
    NUM_ROWS,
    NUM_SONGS,
    SAMPLE_RATE,
    SEEK_SECONDS,
    Mixer,
)

ROW_KEYS = ["1234567890", "qwertyuiop", "asdfghjkl;", "zxcvbnm,./"]
KEY_TO_SLOT = {ch: (row, col) for row, keys in enumerate(ROW_KEYS) for col, ch in enumerate(keys)}
VOLUME_STEP = 0.05
BAR_WIDTH = 40
HELP = {
    "edit": "space: play/pause | m: mark cue | left/right: seek 5s | backspace: delete last cue | "
    "up/down: song | tab: bank | `: page | enter: play mode | ctrl+q: quit",
    "play": "row keys: trigger cue | up/down: song | left/right: volume | space: stop all | "
    "tab: bank | `: page | enter: edit mode | ctrl+q: quit",
}


def fmt_time(samples: int) -> str:
    seconds = samples // SAMPLE_RATE
    return f"{seconds // 60}:{seconds % 60:02d}"


class SamplerApp(App):
    CSS = "Static { height: auto; margin: 1 2 0 2; }"
    BINDINGS = [Binding("tab", "toggle_bank", "Bank", show=False, priority=True)]

    def __init__(self, mixer: Mixer):
        super().__init__()
        self.mixer = mixer
        self.selected = 0
        self.bank = 0
        self.page = 0
        self.mode = "edit"
        self.status = "Edit mode: select a song, press space to play, m to mark cues."

    def compose(self) -> ComposeResult:
        yield Static(id="header")
        for i in range(NUM_ROWS):
            yield Static(id=f"row{i}")
        yield Static(id="status")
        yield Static(id="help")

    def on_mount(self) -> None:
        self.set_interval(0.05, self.refresh_view)
        self.refresh_view()

    def action_toggle_bank(self) -> None:
        self.bank = 1 - self.bank
        self.selected = self.bank * NUM_ROWS + self.selected % NUM_ROWS
        self.refresh_view()

    def on_key(self, event: Key) -> None:
        key = event.key
        if key in ("up", "down"):
            self.selected = (self.selected + (1 if key == "down" else -1)) % NUM_SONGS
            self.bank = self.selected // NUM_ROWS
        elif key == "enter":
            self.mode = "play" if self.mode == "edit" else "edit"
            self.status = f"{self.mode.capitalize()} mode."
        elif event.character == "`":
            self.page = (self.page + 1) % NUM_PAGES
        elif self.mode == "edit" and self.handle_edit_key(event):
            pass
        elif self.mode == "play" and self.handle_play_key(event):
            pass
        elif self.handle_row_key(event.character):
            pass
        else:
            return
        event.stop()
        self.refresh_view()

    def handle_edit_key(self, event: Key) -> bool:
        track = self.mixer.tracks[self.selected]
        if event.key == "space":
            self.mixer.toggle_play(self.selected)
        elif event.key in ("left", "right"):
            self.mixer.seek(self.selected, SEEK_SECONDS if event.key == "right" else -SEEK_SECONDS)
        elif event.character == "m":
            if track is None:
                self.status = "No song in this slot."
                return True
            pos = track.pos
            slot = self.mixer.mark_cue(self.selected)
            if slot is None:
                self.status = "All 20 cues used. Press backspace to delete the last one."
            else:
                save_cues(track.track_id, track.cues)
                self.status = (
                    f"Marked cue {slot % CUES_PER_PAGE + 1} (page {slot // CUES_PER_PAGE + 1}) at {fmt_time(pos)}."
                )
        elif event.key == "backspace":
            if track is not None and self.mixer.remove_last_cue(self.selected):
                save_cues(track.track_id, track.cues)
                self.status = "Deleted last cue."
        else:
            return False
        return True

    def handle_play_key(self, event: Key) -> bool:
        track = self.mixer.tracks[self.selected]
        if event.key in ("left", "right") and track is not None:
            delta = VOLUME_STEP if event.key == "right" else -VOLUME_STEP
            self.mixer.set_volume(self.selected, track.volume + delta)
        elif event.key == "space":
            self.mixer.stop_all()
        else:
            return False
        return True

    def handle_row_key(self, char: str | None) -> bool:
        if char not in KEY_TO_SLOT:
            return False
        row, col = KEY_TO_SLOT[char]
        song = self.bank * NUM_ROWS + row
        self.mixer.trigger(song, self.page * CUES_PER_PAGE + col)
        self.selected = song
        return True

    def refresh_view(self) -> None:
        first = self.bank * NUM_ROWS + 1
        cue_first = self.page * CUES_PER_PAGE + 1
        header = (
            f"{self.mode.upper()} MODE  |  bank {'AB'[self.bank]}: songs {first}-{first + NUM_ROWS - 1}"
            f"  |  page {self.page + 1}: cues {cue_first}-{cue_first + CUES_PER_PAGE - 1}"
        )
        self.query_one("#header", Static).update(Text(header, style="bold"))
        for row in range(NUM_ROWS):
            self.query_one(f"#row{row}", Static).update(self.render_row(row))
        self.query_one("#status", Static).update(self.status)
        self.query_one("#help", Static).update(HELP[self.mode])

    def render_row(self, row: int) -> Text:
        song = self.bank * NUM_ROWS + row
        marker = ">" if song == self.selected else " "
        label = f"{ROW_KEYS[row][0]}..{ROW_KEYS[row][-1]}"
        track = self.mixer.tracks[song]
        if track is None:
            return Text(f"{marker} {label}  (empty)")
        total = max(len(track.data), 1)
        cells = ["."] * BAR_WIDTH
        for slot, cue in enumerate(track.cues):
            if cue is not None:
                on_page = slot // CUES_PER_PAGE == self.page
                cells[min(cue * BAR_WIDTH // total, BAR_WIDTH - 1)] = "|" if on_page else ":"
        cells[min(track.pos * BAR_WIDTH // total, BAR_WIDTH - 1)] = ">" if track.playing else "o"
        used = sum(cue is not None for cue in track.cues)
        volume = "#" * round(track.volume * 10) + "-" * (10 - round(track.volume * 10))
        if track.active_cue is None or track.active_cue // CUES_PER_PAGE != self.page:
            active = "-"
        else:
            active = ROW_KEYS[row][track.active_cue % CUES_PER_PAGE]
        title = track.title[:28].ljust(28)
        return Text(
            f"{marker} {label}  {title}  vol [{volume}]  cues {used:>2}/20  last {active}"
            f"  {fmt_time(track.pos)}/{fmt_time(total)}\n    {''.join(cells)}"
        )
