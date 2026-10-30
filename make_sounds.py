"""Generates the beep sounds in ./sounds (run once: python make_sounds.py)."""
import math
import struct
import wave
from pathlib import Path

RATE = 44100


def write_beep(path, freq, seconds, volume=0.6):
    n = int(RATE * seconds)
    fade = int(RATE * 0.01)  # 10 ms fade in/out avoids clicks
    frames = bytearray()
    for i in range(n):
        env = min(1.0, i / fade, (n - i) / fade)
        sample = volume * env * math.sin(2 * math.pi * freq * i / RATE)
        frames += struct.pack("<h", int(sample * 32767))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


if __name__ == "__main__":
    out = Path(__file__).parent / "sounds"
    out.mkdir(exist_ok=True)
    write_beep(out / "short_beep.wav", 880, 0.15)
    write_beep(out / "long_beep.wav", 1320, 1.2)
