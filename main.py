import asyncio
from database.init_db import init_db, test_connection


async def main():
    await init_db()
    connected = await test_connection()
    print('connected', connected)

if __name__ == '__main__':
    asyncio.run(main())