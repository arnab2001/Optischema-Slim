import asyncio
import asyncpg
import os

async def test_connection():
    try:
        url = os.getenv('DATABASE_URL')
        if not url:
            raise RuntimeError('DATABASE_URL is not set')
        conn = await asyncpg.connect(url)
        print('Connection successful!')
        await conn.close()
    except Exception as e:
        print('Connection failed:', e)

if __name__ == "__main__":
    asyncio.run(test_connection()) 
