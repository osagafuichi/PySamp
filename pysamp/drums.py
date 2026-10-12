from functools import cache

import numpy as np

from pysamp.engine import SAMPLE_RATE

HAT_FREQS = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)
RIDE_FREQS = (260.0, 395.0, 547.0, 678.0, 811.0)
PEAK = 0.7
FADE_SECONDS = 0.005
_rng = np.random.default_rng(1)


def ts(seconds: float) -> np.ndarray:
    return np.arange(int(seconds * SAMPLE_RATE)) / SAMPLE_RATE


def noise(seconds: float) -> np.ndarray:
    return _rng.standard_normal(int(seconds * SAMPLE_RATE))


def unit(x: np.ndarray) -> np.ndarray:
    return x / np.abs(x).max()


def band(x: np.ndarray, low: float, high: float) -> np.ndarray:
    spectrum = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SAMPLE_RATE)
    spectrum[(freqs < low) | (freqs > high)] = 0
    return np.fft.irfft(spectrum, len(x))


def metal(t: np.ndarray, freqs: tuple[float, ...]) -> np.ndarray:
    return sum(np.sign(np.sin(2 * np.pi * f * t)) for f in freqs)


def tone(freq: float, decay: float, seconds: float) -> np.ndarray:
    t = ts(seconds)
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / decay)


def pitched(start: float, end: float, drop: float, decay: float, seconds: float, drive: float = 1.0) -> np.ndarray:
    t = ts(seconds)
    freq = end + (start - end) * np.exp(-t / drop)
    phase = 2 * np.pi * np.cumsum(freq) / SAMPLE_RATE
    return np.tanh(drive * np.sin(phase)) * np.exp(-t / decay)


def kick(start: float, end: float, drop: float, decay: float, seconds: float, drive: float, click: float = 0.0) -> np.ndarray:
    body = pitched(start, end, drop, decay, seconds, drive)
    if click:
        t = ts(seconds)
        body = body + click * unit(band(noise(seconds), 1500, 8000)) * np.exp(-t / 0.003)
    return body


def snare(tone_freq: float, tone_decay: float, noise_decay: float, noise_mix: float, low: float, seconds: float = 0.4) -> np.ndarray:
    t = ts(seconds)
    body = unit(pitched(tone_freq * 1.3, tone_freq, 0.02, tone_decay, seconds))
    hiss = unit(band(noise(seconds), low, 10000)) * np.exp(-t / noise_decay)
    return body * (1 - noise_mix) + hiss * noise_mix


def gated(x: np.ndarray, seconds: float) -> np.ndarray:
    return x * (np.arange(len(x)) < seconds * SAMPLE_RATE)


def clap(decay: float, low: float, high: float) -> np.ndarray:
    t = ts(0.4)
    env = np.zeros_like(t)
    for start in (0.0, 0.011, 0.022):
        env += np.where(t >= start, np.exp(-(t - start) / 0.007), 0)
    env += 0.5 * np.where(t >= 0.03, np.exp(-(t - 0.03) / decay), 0)
    return unit(band(noise(0.4), low, high)) * env


def rimshot() -> np.ndarray:
    t = ts(0.15)
    return tone(500, 0.02, 0.15) + 0.7 * tone(1700, 0.015, 0.15) + 0.5 * unit(band(noise(0.15), 2000, 9000)) * np.exp(-t / 0.01)


def side_stick() -> np.ndarray:
    t = ts(0.1)
    return tone(400, 0.015, 0.1) + 0.6 * tone(1150, 0.01, 0.1) + 0.3 * unit(band(noise(0.1), 2000, 8000)) * np.exp(-t / 0.005)


def snap() -> np.ndarray:
    t = ts(0.12)
    return unit(band(noise(0.12), 1500, 4500)) * np.exp(-t / 0.02) + 0.5 * tone(2000, 0.02, 0.12)


def hat(decay: float, seconds: float, low: float = 6000) -> np.ndarray:
    t = ts(seconds)
    sound = unit(band(metal(t, HAT_FREQS), low, 16000)) + 0.3 * unit(band(noise(seconds), low, 16000))
    return sound * np.exp(-t / decay)


def shaker(decay: float, seconds: float, low: float, high: float) -> np.ndarray:
    t = ts(seconds)
    return unit(band(noise(seconds), low, high)) * np.minimum(t / 0.015, 1) * np.exp(-t / decay)


def ride() -> np.ndarray:
    t = ts(1.2)
    return unit(band(metal(t, RIDE_FREQS), 3000, 12000)) * np.exp(-t / 0.5) + 0.4 * tone(3200, 0.3, 1.2)


def ride_bell() -> np.ndarray:
    return tone(2500, 0.4, 0.8) + 0.6 * tone(3730, 0.3, 0.8) + 0.4 * tone(5150, 0.2, 0.8)


def crash(seconds: float, decay: float, low: float, high: float) -> np.ndarray:
    t = ts(seconds)
    sound = unit(band(metal(t, HAT_FREQS), low, high)) + 0.6 * unit(band(noise(seconds), low, high))
    return sound * np.minimum(t / 0.003, 1) * np.exp(-t / decay)


def cowbell() -> np.ndarray:
    t = ts(0.4)
    return unit(band(metal(t, (540.0, 800.0)), 400, 3000)) * (0.7 * np.exp(-t / 0.02) + 0.3 * np.exp(-t / 0.12))


def triangle() -> np.ndarray:
    return sum(tone(f, 0.9, 1.2) for f in (3500, 5300, 7600, 9700))


def tambourine() -> np.ndarray:
    t = ts(0.5)
    return (unit(band(metal(t, HAT_FREQS), 5000, 15000)) + 0.5 * unit(band(noise(0.5), 5000, 15000))) * np.exp(-t / 0.15)


def conga(freq: float) -> np.ndarray:
    t = ts(0.4)
    slap = 0.4 * unit(band(noise(0.4), 1000, 4000)) * np.exp(-t / 0.01)
    return pitched(freq * 1.15, freq, 0.02, 0.12, 0.4) + slap


def laser() -> np.ndarray:
    t = ts(0.3)
    phase = 2 * np.pi * np.cumsum(150 + 2400 * np.exp(-t * 9)) / SAMPLE_RATE
    return np.sin(phase) * np.exp(-t / 0.15)


def woodblock() -> np.ndarray:
    return tone(1800, 0.03, 0.15) + 0.5 * tone(2700, 0.02, 0.15)


# (name, sound, level, choke group); group 0 never chokes. Listed row by row,
# left to right, matching the number, QWERTY, ASDF and ZXCV key rows.
PADS = [
    ("Cowbell", cowbell, 0.8, 0),
    ("Clave", lambda: tone(2500, 0.03, 0.15), 0.8, 0),
    ("Woodblock", woodblock, 0.8, 0),
    ("Triangle", triangle, 0.6, 0),
    ("Tambourine", tambourine, 0.8, 0),
    ("Conga High", lambda: conga(330), 0.9, 0),
    ("Conga Low", lambda: conga(220), 0.9, 0),
    ("Bongo", lambda: conga(450), 0.8, 0),
    ("Maracas", lambda: shaker(0.03, 0.15, 6000, 14000), 0.6, 0),
    ("Laser", laser, 0.7, 0),
    ("Closed Hat", lambda: hat(0.025, 0.15), 0.7, 1),
    ("Tight Hat", lambda: hat(0.012, 0.1, 7000), 0.7, 1),
    ("Open Hat", lambda: hat(0.25, 0.8), 0.7, 1),
    ("Pedal Hat", lambda: hat(0.04, 0.2, 5000), 0.45, 1),
    ("Shaker", lambda: shaker(0.06, 0.25, 5000, 12000), 0.6, 0),
    ("Ride", ride, 0.65, 0),
    ("Ride Bell", ride_bell, 0.6, 0),
    ("Crash", lambda: crash(1.6, 0.45, 3000, 14000), 0.75, 0),
    ("Dark Crash", lambda: crash(1.8, 0.7, 2000, 11000), 0.75, 0),
    ("Splash", lambda: crash(0.8, 0.2, 4000, 15000), 0.7, 0),
    ("Snare", lambda: snare(190, 0.07, 0.12, 0.65, 1500), 0.9, 0),
    ("Boom Snare", lambda: snare(150, 0.1, 0.18, 0.55, 800, 0.5), 0.9, 0),
    ("House Snare", lambda: snare(220, 0.05, 0.2, 0.75, 2500), 0.85, 0),
    ("Clap", lambda: clap(0.12, 900, 3800), 0.9, 0),
    ("House Clap", lambda: clap(0.2, 1200, 5000), 0.85, 0),
    ("Rimshot", rimshot, 0.8, 0),
    ("Side Stick", side_stick, 0.7, 0),
    ("Snap", snap, 0.7, 0),
    ("Ghost Snare", lambda: snare(190, 0.04, 0.06, 0.6, 1500, 0.2), 0.4, 0),
    ("Gated Snare", lambda: gated(snare(200, 0.06, 0.1, 0.7, 1500), 0.15), 0.9, 0),
    ("808 Kick", lambda: kick(150, 45, 0.04, 0.35, 0.8, 1.5), 1.0, 0),
    ("Boom Kick", lambda: kick(110, 38, 0.06, 0.7, 1.4, 2.0), 1.0, 0),
    ("House Kick", lambda: kick(180, 50, 0.025, 0.2, 0.5, 2.5, 0.4), 1.0, 0),
    ("Punch Kick", lambda: kick(200, 60, 0.02, 0.14, 0.4, 1.8, 0.5), 1.0, 0),
    ("Tight Kick", lambda: kick(130, 55, 0.015, 0.09, 0.3, 1.2), 1.0, 0),
    ("Floor Tom", lambda: pitched(126, 90, 0.05, 0.3, 0.7), 0.95, 0),
    ("Low Tom", lambda: pitched(168, 120, 0.05, 0.25, 0.6), 0.95, 0),
    ("Mid Tom", lambda: pitched(224, 160, 0.05, 0.22, 0.5), 0.95, 0),
    ("High Tom", lambda: pitched(308, 220, 0.05, 0.2, 0.5), 0.95, 0),
    ("Electro Tom", lambda: pitched(400, 150, 0.12, 0.3, 0.6, 2.0), 0.95, 0),
]

NAMES = [name for name, *_ in PADS]


def finish(sound: np.ndarray, level: float) -> np.ndarray:
    sound = sound / np.abs(sound).max() * PEAK * level
    fade = int(FADE_SECONDS * SAMPLE_RATE)
    sound[-fade:] *= np.linspace(1, 0, fade)
    return np.column_stack([sound, sound]).astype(np.float32)


@cache
def pads() -> tuple[tuple[np.ndarray, int], ...]:
    return tuple((finish(sound(), level), group) for _, sound, level, group in PADS)
