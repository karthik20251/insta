"""List all edge-tts voices matching a name."""
import asyncio
import sys
import edge_tts

NAME = sys.argv[1] if len(sys.argv) > 1 else "Rosa"


async def main() -> None:
    voices = await edge_tts.list_voices()
    matches = [v for v in voices if NAME.lower() in v["ShortName"].lower() or NAME.lower() in v.get("FriendlyName", "").lower()]
    if not matches:
        print(f"No voices matching '{NAME}'")
        return
    print(f"Voices matching '{NAME}':\n")
    for v in matches:
        print(f"  {v['ShortName']:35s}  {v['Gender']:6s}  {v.get('Locale', '?'):8s}  {v.get('FriendlyName', '?')}")


if __name__ == "__main__":
    asyncio.run(main())
