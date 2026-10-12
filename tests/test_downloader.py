import tempfile
from pathlib import Path

import yt_dlp

import pysamp.downloader as dl

BOT = yt_dlp.utils.DownloadError("ERROR: [youtube] x: Sign in to confirm you're not a bot.")


def run_with(fake):
    calls = []

    def fetch(url, dest_dir, browser):
        calls.append(browser)
        return fake(browser)

    dl.fetch = fetch
    dl.working_browser = None
    return calls


def test_plain_download_needs_no_cookies() -> None:
    with tempfile.TemporaryDirectory() as d:
        calls = run_with(lambda b: (Path("a.wav"), "A"))
        assert dl.download("u", Path(d)) == (Path("a.wav"), "A")
        assert calls == [None]


def test_bot_check_falls_back_to_working_browser() -> None:
    with tempfile.TemporaryDirectory() as d:
        def fake(browser):
            if browser == "firefox":
                return Path("a.wav"), "A"
            if browser is None:
                raise BOT
            raise RuntimeError("no such browser profile")

        calls = run_with(fake)
        assert dl.download("u", Path(d)) == (Path("a.wav"), "A")
        assert calls == [None, "chrome", "safari", "firefox"]
        assert dl.working_browser == "firefox"

        # The next download goes straight to the browser that worked.
        calls.clear()
        dl.download("u", Path(d))
        assert calls == ["firefox"]


def test_all_browsers_fail_gives_clear_error() -> None:
    with tempfile.TemporaryDirectory() as d:
        def fake(browser):
            raise BOT if browser is None else RuntimeError("nope")

        run_with(fake)
        try:
            dl.download("u", Path(d))
        except RuntimeError as exc:
            assert str(exc) == dl.BLOCKED_MESSAGE
        else:
            raise AssertionError("expected RuntimeError")


def test_other_errors_are_not_retried() -> None:
    with tempfile.TemporaryDirectory() as d:
        def fake(browser):
            raise yt_dlp.utils.DownloadError("ERROR: Video unavailable")

        calls = run_with(fake)
        try:
            dl.download("u", Path(d))
        except yt_dlp.utils.DownloadError:
            assert calls == [None]
        else:
            raise AssertionError("expected DownloadError")


if __name__ == "__main__":
    test_plain_download_needs_no_cookies()
    test_bot_check_falls_back_to_working_browser()
    test_all_browsers_fail_gives_clear_error()
    test_other_errors_are_not_retried()
    print("downloader tests passed")
