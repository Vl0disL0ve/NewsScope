import asyncio
import telethon
from parser import TGParser


async def main():
    async with TGParser() as parser:
        try:
            data = await parser.parse_channel("sberinvestments", limit=5)
            for row in data:
                print(" | ".join(str(x) for x in row))
        except telethon.errors.FloodWaitError as e:
            print(f"Time limit. Wait {e.seconds} seconds.")
            exit()
        except Exception as e:
            print(f"Error: {e}")
            exit()


if __name__ == "__main__":
    asyncio.run(main())
