import streamlit as st
import asyncio
import json
import os
import shutil
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

st.set_page_config(page_title="MCP Control Center", page_icon="🎛️", layout="wide")
st.header("🎛️ MCP Control Center")

# 1. Configuration & State
CONFIG_FILE = "mcp_config.json"

if "mcp_resources" not in st.session_state:
    st.session_state.mcp_resources = []
if "mcp_tools" not in st.session_state:
    st.session_state.mcp_tools = []
if "last_connected_server" not in st.session_state:
    st.session_state.last_connected_server = None
if "context_context" not in st.session_state:
    st.session_state.context_context = [] # List of injected resource contents

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"mcpServers": {}}

config = load_config()

# Helper to run async MCP calls
async def connect_and_fetch(server_name, server_config):
    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config["args"],
        env={**os.environ, **server_config.get("env", {})}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Fetch Resources
            try:
                resources_resp = await session.list_resources()
                resources = resources_resp.resources if resources_resp else []
            except Exception:
                # Server might not support resources
                resources = []
            
            # Fetch Tools
            try:
                tools_resp = await session.list_tools()
                tools = tools_resp.tools if tools_resp else []
            except Exception:
                tools = []
            
            return resources, tools

async def run_tool(server_name, server_config, tool_name, tool_args):
    server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config["args"],
        env={**os.environ, **server_config.get("env", {})}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=tool_args)
            return result

async def read_resource(server_name, server_config, resource_uri):
     server_params = StdioServerParameters(
        command=server_config["command"],
        args=server_config["args"],
        env={**os.environ, **server_config.get("env", {})}
    )
    
     async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.read_resource(resource_uri)
            return result

# 2. Tabs
tab_servers, tab_resources, tab_tools, tab_context = st.tabs([
    "🖥️ Servers", "🗂️ Resources", "🛠️ Tools", "🧠 Context"
])

# --- TAB 1: Servers ---
with tab_servers:
    st.subheader("Server Manager")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        server_names = list(config["mcpServers"].keys())
        selected_server = st.selectbox("Select Server", server_names)
        
        if st.button("Connect & Refresh"):
            if selected_server:
                with st.spinner(f"Connecting to {selected_server}..."):
                    try:
                        resources, tools = asyncio.run(connect_and_fetch(
                            selected_server, 
                            config["mcpServers"][selected_server]
                        ))
                        st.session_state.mcp_resources = resources
                        st.session_state.mcp_tools = tools
                        st.session_state.last_connected_server = selected_server
                        st.success(f"Connected! Found {len(resources)} resources and {len(tools)} tools.")
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
                        # Check dependencies
                        if "npx" in config["mcpServers"][selected_server]["command"]:
                             if not shutil.which("npx"):
                                 st.warning("`npx` not found. Is Node.js installed?")
    
    with col2:
        if selected_server:
            st.code(json.dumps(config["mcpServers"][selected_server], indent=2), language="json")

# --- TAB 2: Resources ---
with tab_resources:
    st.subheader("Resource Browser")
    if not st.session_state.mcp_resources:
        st.info("No resources loaded. Connect to a server first.")
    else:
        # Display as a table or list
        for res in st.session_state.mcp_resources:
            with st.expander(f"📄 {res.name} ({res.mimeType})"):
                st.write(f"**URI**: `{res.uri}`")
                st.write(res.description)
                
                if st.button(f"Inject Context for {res.name}", key=f"inj_{res.uri}"):
                    # Read content
                    try:
                        with st.spinner("Reading content..."):
                             content_result = asyncio.run(read_resource(
                                 st.session_state.last_connected_server,
                                 config["mcpServers"][st.session_state.last_connected_server],
                                 res.uri
                             ))
                             # Assuming content is text for now
                             text = content_result.contents[0].text
                             st.session_state.context_context.append({
                                 "source": res.uri,
                                 "content": text
                             })
                             st.success(f"Injected {len(text)} chars into Context!")
                    except Exception as e:
                        st.error(f"Failed to read resource: {e}")

# --- TAB 3: Tools ---
with tab_tools:
    st.subheader("Tool Registry & Test Bench")
    if not st.session_state.mcp_tools:
        st.info("No tools loaded. Connect to a server first.")
    else:
        tool_names = [t.name for t in st.session_state.mcp_tools]
        selected_tool_name = st.selectbox("Select Tool", tool_names)
        
        # Find tool obj
        selected_tool = next((t for t in st.session_state.mcp_tools if t.name == selected_tool_name), None)
        
        if selected_tool:
            st.markdown(f"**Description**: {selected_tool.description}")
            st.markdown("**Schema**:")
            st.json(selected_tool.inputSchema)
            
            # Form generator
            with st.form(key="tool_form"):
                st.markdown("### Arguments")
                args = {}
                # Simple parsing of schema properties
                props = selected_tool.inputSchema.get("properties", {})
                for prop_name, prop_def in props.items():
                    args[prop_name] = st.text_input(f"{prop_name} ({prop_def.get('type', 'string')})", help=prop_def.get("description"))
                
                submitted = st.form_submit_button("Run Tool")
            
            if submitted:
                 try:
                    with st.spinner("Running tool..."):
                        # Clean and Cast Arguments
                        cleaned_args = {}
                        props = selected_tool.inputSchema.get("properties", {})
                        for k, v in args.items():
                            if v is None or v == "":
                                continue # Skip empty arguments
                            
                            prop_type = props.get(k, {}).get("type", "string")
                            if prop_type in ["integer", "number"]:
                                try:
                                    if prop_type == "integer":
                                        cleaned_args[k] = int(v)
                                    else:
                                        cleaned_args[k] = float(v)
                                except ValueError:
                                    st.error(f"Invalid number for argument '{k}'")
                                    raise
                            else:
                                cleaned_args[k] = v

                        result = asyncio.run(run_tool(
                            st.session_state.last_connected_server,
                            config["mcpServers"][st.session_state.last_connected_server],
                            selected_tool_name,
                            cleaned_args
                        ))
                        st.session_state.latest_tool_result = {
                            "tool": selected_tool_name,
                            "result": result
                        }
                 except Exception as e:
                    st.error(f"Tool execution failed: {e}")

            # Display Result (Outside Form)
            if "latest_tool_result" in st.session_state and st.session_state.latest_tool_result:
                res = st.session_state.latest_tool_result
                st.subheader(f"Result: {res['tool']}")
                
                # Result is a CallToolResult
                for content in res["result"].content:
                    if content.type == "text":
                        st.code(content.text)
                        # Add to Context Button works here because it is outside the form
                        if st.button("💾 Add to Active Context", key=f"save_ctx_{res['tool']}"):
                            st.session_state.context_context.append({
                                "source": f"Tool: {res['tool']}",
                                "content": content.text
                            })
                            st.success("Added to Active Context!")
                    elif content.type == "image":
                        st.image(content.data)

# --- TAB 4: Context ---
with tab_context:
    st.subheader("Active Context Memory")
    if not st.session_state.context_context:
        st.info("No context injected yet.")
    else:
        for i, item in enumerate(st.session_state.context_context):
            with st.expander(f"ctx #{i+1}: {item['source']}"):
                st.text_area("Content", item['content'], height=200, key=f"ctx_txt_{i}")
                if st.button("Remove", key=f"rm_{i}"):
                    st.session_state.context_context.pop(i)
                    st.rerun()

