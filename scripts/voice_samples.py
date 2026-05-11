"""Generate sample audio for Abeo (Nigerian) and James (Philippine) voices.

Run, then play both files to pick a voice:
    start output/voice_sample_abeo.mp3
    start output/voice_sample_james.mp3
"""
import asyncio
from pathlib import Path
import edge_tts

OUT = Path(__file__).parent.parent / "output"
OUT.mkdir(exist_ok=True)

TEXT = (
    "Law 3. Conceal your intentions. "
    "Keep people off-balance and in the dark by never revealing the purpose behind your actions. "
    "For your life: Don't announce you're job-hunting. Keep building quietly, line up the offer, "
    "then make your move from a position of strength."
)

VOICES = {
    "abeo": "en-NG-AbeoNeural",
    "james": "en-PH-JamesNeural",
    "prabhat": "en-IN-PrabhatNeural",
    "neerja": "en-IN-NeerjaNeural",
    "rosa": "en-PH-RosaNeural",
    "ryan": "en-GB-RyanNeural",
}


async def gen(name: str, voice: str) -> None:
    out = OUT / f"voice_sample_{name}.mp3"
    communicate = edge_tts.Communicate(TEXT, voice)
    await communicate.save(str(out))
    print(f"  [OK] {out.name}  {out.stat().st_size // 1024} KB  ({voice})")


async def main() -> None:
    for name, voice in VOICES.items():
        await gen(name, voice)


if __name__ == "__main__":
    asyncio.run(main())
