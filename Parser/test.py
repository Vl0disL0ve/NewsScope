import asyncio
import sys
from pathlib import Path
import telethon

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Parser import TGParser

import datetime


async def main():
    start_date = datetime.datetime(2026, 1, 25)
    end_date = datetime.datetime(2026, 1, 31)

    async with TGParser() as parser:
        try:
            data = await parser.parse_channel(channel="sberinvestments",
                                               start_date=start_date,
                                               end_date=end_date)
            for row in data:
                print(" | ".join(str(x) for x in row))
                print("-" * 80)
        except telethon.errors.FloodWaitError as e:
            print(f"Time limit. Wait {e.seconds} seconds.")
            exit()
        except Exception as e:
            print(f"Error: {e}")
            exit()


if __name__ == "__main__":
    asyncio.run(main())
