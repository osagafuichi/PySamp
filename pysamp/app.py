from rich.text import Text
from textual.app import App, ComposeResult
from textual.events import Key
from textual.widgets import Static

from pysamp.engine import NUM_ROWS, Mixer

ROW_KEYS = ["1234567890", "qwertyuiop", "asdfghjkl;", "zxcvbnm,./"]
KEY_TO_SLOT = {ch: (row, cue) for row, keys in enumerate(ROW_KEYS) for cue, ch in enumerate(keys)}
VOLUME_STEP = 0.05
BAR_WIDTH = 40
HELP = "row keys: trigger cue | up/down: select row | left/right: volume | space: stop all | ctrl+q: quit"


class SamplerApp(App):
    CSS = "Static { height: auto; margin: 1 2 0 2; }"

    def __init__(self, mixer: Mixer):
        super().__init__()
        self.mixer = mixer
        self.selected = 0

    def compose(self) -> ComposeResult:
        for i in range(NUM_ROWS):
            yield Static(id=f"row{i}")
        yield Static(HELP, id="help")

    def on_mount(self) -> None:
        self.set_interval(0.05, self.refresh_rows)
        self.refresh_rows()

    def on_key(self, event: Key) -> None:
        if event.key == "up":
            self.selected = (self.selected - 1) % NUM_ROWS
        elif event.key == "down":
            self.selected = (self.selected + 1) % NUM_ROWS
        elif event.key in ("left", "right"):
            track = self.mixer.tracks[self.selected]
            if track is not None:
                delta = VOLUME_STEP if event.key == "right" else -VOLUME_STEP
                self.mixer.set_volume(self.selected, track.volume + delta)
        elif event.key == "space":
            self.mixer.stop_all()
        elif event.character in KEY_TO_SLOT:
            row, cue = KEY_TO_SLOT[event.character]
            self.mixer.trigger(row, cue)
            self.selected = row
        else:
            return
        event.stop()
        self.refresh_rows()

    def refresh_rows(self) -> None:
        for i in range(NUM_ROWS):
            self.query_one(f"#row{i}", Static).update(self.render_row(i))

    def render_row(self, i: int) -> Text:
        marker = ">" if i == self.selected else " "
        track = self.mixer.tracks[i]
        if track is None:
            return Text(f"{marker} {ROW_KEYS[i][0]}..{ROW_KEYS[i][-1]}  (empty)")
        filled = round(track.volume * 10)
        volume = "#" * filled + "-" * (10 - filled)
        total = len(track.data)
        cells = ["."] * BAR_WIDTH
        for cue in track.cues:
            cells[min(cue * BAR_WIDTH // total, BAR_WIDTH - 1)] = "|"
        cells[min(track.pos * BAR_WIDTH // total, BAR_WIDTH - 1)] = ">" if track.playing else "o"
        cue_label = "-" if track.active_cue is None else ROW_KEYS[i][track.active_cue]
        title = track.title[:30].ljust(30)
        return Text(f"{marker} {ROW_KEYS[i][0]}..{ROW_KEYS[i][-1]}  {title}  vol [{volume}]  cue {cue_label}\n    {''.join(cells)}")
