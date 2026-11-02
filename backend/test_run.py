import asyncio
import httpx
from app.main import app

async def run():
    print("Starting client...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("Sending request...")
        r = await client.get("/api/health")
        print("Response received:", r.status_code, r.json())

if __name__ == "__main__":
    asyncio.run(run())
