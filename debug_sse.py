import asyncio
import httpx

async def test_sse_raw():
    url = "https://mcp.alphavantage.co/mcp?apikey=GWX88EWNSCDGAO4C"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "debug-script", "version": "1.0"}
        },
        "id": 1
    }
    
    print(f"--- POSTing to: {url} ---")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
            print(f"Status: {response.status_code}")
            print(f"Headers: {response.headers}")
            print(f"Body: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sse_raw())
