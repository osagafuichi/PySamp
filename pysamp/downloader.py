import os
from pathlib import Path

import imageio_ffmpeg
import yt_dlp

from pysamp.engine import SAMPLE_RATE

BROWSERS = ["chrome", "safari", "firefox", "edge", "brave"]
BOT_CHECK = "Sign in to confirm"
BLOCKED_MESSAGE = (
    "YouTube blocked the download (bot check). Log in to YouTube in Chrome, Safari or Firefox "
    "and try again, or load a local audio file."
)

working_browser: str | None = None


def fetch(url: str, dest_dir: Path, browser: str | None) -> tuple[Path, str]:
    opts = {
        "format": "bestaudio/best",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "noplaylist": True,
        "quiet": True,
        "noprogress": True,
        "no_warnings": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "postprocessor_args": {"extractaudio": ["-ar", str(SAMPLE_RATE), "-ac", "2"]},
    }
    if browser:
        opts["cookiesfrombrowser"] = (browser,)
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        wav = dest_dir / f"{info['id']}.wav"
        if not wav.exists():
            ydl.download([url])
    return wav, info.get("title", info["id"])


def download(url: str, dest_dir: Path) -> tuple[Path, str]:
    global working_browser
    dest_dir.mkdir(parents=True, exist_ok=True)
    forced = os.environ.get("PYSAMP_BROWSER")
    first = forced or working_browser
    try:
        return fetch(url, dest_dir, first)
    except yt_dlp.utils.DownloadError as exc:
        if BOT_CHECK not in str(exc):
            raise
    for browser in [forced] if forced else [b for b in BROWSERS if b != first]:
        try:
            result = fetch(url, dest_dir, browser)
        except Exception:
            continue
        working_browser = browser
        return result
    raise RuntimeError(BLOCKED_MESSAGE)
