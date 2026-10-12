import queue
import threading
from pathlib import Path

import numpy as np
import soundfile as sf


class Recorder:
    def __init__(self, path: Path, rate: int, channels: int = 2):
        self.path = path
        self.frames = 0
        self._file = sf.SoundFile(str(path), "w", rate, channels, format="WAV", subtype="PCM_16")
        self._queue: queue.SimpleQueue = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def push(self, block: np.ndarray) -> None:
        self.frames += len(block)
        self._queue.put(block.copy())

    def finish(self) -> None:
        self._queue.put(None)
        self._thread.join()

    def _run(self) -> None:
        while (block := self._queue.get()) is not None:
            self._file.write(block)
        self._file.close()
