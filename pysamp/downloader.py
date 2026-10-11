from pathlib import Path

import imageio_ffmpeg
import yt_dlp

from pysamp.engine import SAMPLE_RATE


def download(url: str, dest_dir: Path) -> tuple[Path, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
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
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        wav = dest_dir / f"{info['id']}.wav"
        if not wav.exists():
            ydl.download([url])
    return wav, info.get("title", info["id"])
