import asyncio
import os
import json
import shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Define the server config manually for debugging
SERVER_CONFIG = {
    "command": "npx",
    "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/songzigg/PythonProjects/streamlit-agent"
    ],
    "env": {}
}

async def debug_connection():
    print(f"Checking for npx: {shutil.which('npx')}")
    
    server_params = StdioServerParameters(
        command=SERVER_CONFIG["command"],
        args=SERVER_CONFIG["args"],
        env={**os.environ, **SERVER_CONFIG.get("env", {})}
    )
    
    print("Starting stdio_client...")
    try:
        async with stdio_client(server_params) as (read, write):
            print("Client started. Initializing session...")
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Session initialized!")
                
                # Try Tools first (FS server definitely has these)
                try:
                    tools_resp = await session.list_tools()
                    print(f"Found {len(tools_resp.tools)} tools.")
                    for tool in tools_resp.tools:
                        print(f" - {tool.name}")
                except Exception as e:
                    print(f"Failed to list tools: {e}")

                # Try Resources
                try:
                    resources_resp = await session.list_resources()
                    print(f"Found {len(resources_resp.resources)} resources.")
                except Exception as e:
                    print(f"Failed to list resources (Expected if server doesn't support it): {e}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_connection())
