"""Generate Kannada voice samples for Day 4 content."""
import asyncio
from pathlib import Path
import edge_tts

OUT = Path(__file__).parent.parent / "output"
OUT.mkdir(exist_ok=True)

# Day 4 — Law 3: Conceal Your Intentions (Kannada translation)
TEXT_KN = (
    "ಕಾನೂನು ಮೂರು. ನಿಮ್ಮ ಉದ್ದೇಶಗಳನ್ನು ಮರೆಮಾಚಿ. "
    "ಜನರನ್ನು ಸಮತೋಲನದಿಂದ ಹೊರಗಿಡಲು ಮತ್ತು ಕತ್ತಲೆಯಲ್ಲಿ ಇರಿಸಲು, "
    "ನಿಮ್ಮ ಕ್ರಿಯೆಗಳ ಹಿಂದಿನ ಉದ್ದೇಶವನ್ನು ಎಂದಿಗೂ ಬಹಿರಂಗಪಡಿಸಬೇಡಿ. "
    "ನಿಮ್ಮ ಜೀವನಕ್ಕಾಗಿ: ನೀವು ಕೆಲಸ ಹುಡುಕುತ್ತಿರುವುದನ್ನು ಘೋಷಿಸಬೇಡಿ. "
    "ಶಾಂತವಾಗಿ ನಿರ್ಮಿಸುತ್ತಾ ಇರಿ, ಆಫರ್ ಪಡೆಯಿರಿ, "
    "ನಂತರ ಶಕ್ತಿಯ ಸ್ಥಾನದಿಂದ ನಿಮ್ಮ ಚಲನೆ ಮಾಡಿ."
)

VOICES = {
    "gagan": "kn-IN-GaganNeural",   # Male
    "sapna": "kn-IN-SapnaNeural",   # Female
}


async def gen(name: str, voice: str) -> None:
    out = OUT / f"voice_sample_{name}_kn.mp3"
    communicate = edge_tts.Communicate(TEXT_KN, voice)
    await communicate.save(str(out))
    print(f"  [OK] {out.name}  {out.stat().st_size // 1024} KB  ({voice})")


async def main() -> None:
    for name, voice in VOICES.items():
        await gen(name, voice)


if __name__ == "__main__":
    asyncio.run(main())
