import httpx
import json
from types import SimpleNamespace

class StatelessMcpSession:
    def __init__(self, url):
        self.url = url
        self.message_id = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _post(self, method, params=None):
        self.message_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.message_id,
            "method": method,
            "params": params or {}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            data = response.json()
            
            if "error" in data:
                raise Exception(f"RPC Error: {data['error']}")
            
            return data.get("result")

    # Mimic ClientSession methods
    
    async def initialize(self):
        return await self._post("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "streamlit-agent-http", "version": "1.0"}
        })

    async def list_resources(self):
        """Returns object with .resources attribute."""
        res = await self._post("resources/list")
        # Convert list of dicts to list of objects
        resources_list = []
        for r in res.get("resources", []):
            resources_list.append(SimpleNamespace(**r))
        
        return SimpleNamespace(resources=resources_list)

    async def list_tools(self):
        """Returns object with .tools attribute."""
        res = await self._post("tools/list")
        tools_list = []
        for t in res.get("tools", []):
            tools_list.append(SimpleNamespace(**t))
        return SimpleNamespace(tools=tools_list)

    async def call_tool(self, name, arguments):
        """Returns object with .content attribute."""
        res = await self._post("tools/call", {"name": name, "arguments": arguments})
        
        content_list = []
        for c in res.get("content", []):
            content_list.append(SimpleNamespace(**c))
            
        return SimpleNamespace(content=content_list)
        
    async def read_resource(self, uri):
         """Returns object with .contents attribute."""
         res = await self._post("resources/read", {"uri": uri})
         
         contents_list = []
         for c in res.get("contents", []): # Note: 'contents' usually
             contents_list.append(SimpleNamespace(**c))
             
         return SimpleNamespace(contents=contents_list)
