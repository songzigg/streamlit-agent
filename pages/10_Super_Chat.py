import streamlit as st
import json
import time
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool, tool
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_community.utilities import SerpAPIWrapper

from utils import configure_api_key, configure_serpapi_key
import asyncio
import os
import io
import pandas as pd
from pypdf import PdfReader
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
# from mcp.client.sse import sse_client
from mcp_http_client import StatelessMcpSession
from langchain_core.tools import StructuredTool

st.set_page_config(page_title="Super Chat", page_icon="🦸‍♂️", layout="wide")

# --- Custom Styling ---
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .stStatus {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

st.header("🦸‍♂️ Super Chat")
st.caption("One Agent. Infinite Possibilities. (Search + MCP + Vision + Memory)")

# ==============================================================================
# 1. HELPER FUNCTIONS (Must be defined before usage)
# ==============================================================================

def process_uploaded_file(uploaded_file):
    """Extract text content from uploaded file."""
    try:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif uploaded_file.type == "text/csv":
            df = pd.read_csv(uploaded_file)
            return df.to_markdown(index=False)
        else:
            # Assume text/code
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            return stringio.read()
    except Exception as e:
        return f"Error reading file: {e}"

def get_serp_tool():
    try:
        serp_key = configure_serpapi_key()
        search = SerpAPIWrapper(serpapi_api_key=serp_key)
        return Tool(
            name="WebSearch",
            func=search.run,
            description="Useful for searching the internet for current events and facts."
        )
    except:
        return None

async def run_tool_async(server_config, tool_name, tool_args):
    """Bridge for running MCP tools (HTTP or Stdio)."""
    if "url" in server_config:
        # HTTP Stateless Connection
        async with StatelessMcpSession(server_config["url"]) as session:
            await session.initialize()
            return await session.call_tool(tool_name, arguments=tool_args)
                
    elif "command" in server_config:
        # Stdio Connection
        server_params = StdioServerParameters(
            command=server_config["command"],
            args=server_config["args"],
            env={**os.environ, **server_config.get("env", {})}
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments=tool_args)
    else:
        raise ValueError("Invalid Server Config: Missing 'command' or 'url'")

def get_mcp_tools(enable_mcp):
    if not enable_mcp:
        return []
    
    config_path = "mcp_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            full_config = json.load(f)
    else:
        return []
    
    mcp_langchain_tools = []
    
    if "mcp_tools" in st.session_state and st.session_state.mcp_tools:
        server_name = st.session_state.get("last_connected_server")
        if server_name and server_name in full_config["mcpServers"]:
            server_config = full_config["mcpServers"][server_name]
            
            for tool_obj in st.session_state.mcp_tools:
                def create_wrapper(t_name, s_config):
                    def wrapper(**kwargs):
                        try:
                            res = asyncio.run(run_tool_async(s_config, t_name, kwargs))
                            results = []
                            for c in res.content:
                                if c.type == "text":
                                    results.append(c.text)
                                elif c.type == "image":
                                    img_fmt = c.mimeType or "image/png"
                                    results.append(f"![Generated Image](data:{img_fmt};base64,{c.data})")
                            return "\n".join(results)
                        except Exception as e:
                            return f"Error executing tool {t_name}: {e}"
                    return wrapper
                
                mcp_langchain_tools.append(StructuredTool.from_function(
                    func=create_wrapper(tool_obj.name, server_config),
                    name=tool_obj.name,
                    description=f"{tool_obj.description} (MCP Tool from {server_name})"
                ))
    
    return mcp_langchain_tools 

# ==============================================================================
# 2. STATE & CONFIGURATION
# ==============================================================================

if "super_messages" not in st.session_state:
    st.session_state.super_messages = [{"role": "assistant", "content": "I am connected to all your systems. How can I help? 🦸‍♂️"}]

deepseek_api_key = configure_api_key()

# Sidebar Configuration
with st.sidebar:
    st.header("Configuration")
    enable_mcp = st.checkbox("🔌 Enable MCP Tools", value=False, help="Connects to the last active MCP server.")
    
    if enable_mcp and not get_mcp_tools(True):
         st.warning("No MCP tools found! Go to 'MCP Control Center' and Connect first.")

# ==============================================================================
# 3. TOOL LOADING & AGENT SETUP
# ==============================================================================

tools = []
serp_tool = get_serp_tool()
if serp_tool:
    tools.append(serp_tool)

if enable_mcp:
    tools.extend(get_mcp_tools(enable_mcp))

# Sidebar display (post-load)
with st.sidebar:
    st.markdown(f"**Loaded Tools:** {len(tools)}")
    for t in tools:
        st.markdown(f"- 🔧 {t.name}")
    st.divider()   
    
    if st.button("📥 Download Conversation"):
        chat_str = json.dumps(st.session_state.super_messages, indent=2, ensure_ascii=False)
        st.download_button(
            label="Save JSON",
            data=chat_str,
            file_name=f"super_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Setup LLM
llm = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    temperature=0.7,
    streaming=True
)

# Prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a Super Assistant. You have access to Web Search, Image Generation, and other tools. "
               "Use them whenever necessary. Answer nicely and use emojis."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

if "super_memory" not in st.session_state:
    st.session_state.super_memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")

# Construct Agent
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    memory=st.session_state.super_memory,
    handle_parsing_errors=True
)

# ==============================================================================
# 4. CHAT INTERFACE
# ==============================================================================

for msg in st.session_state.super_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"], unsafe_allow_html=True) # Allow HTML for data URI images

# File Uploader
with st.expander("📎 Attach File (PDF, CSV, TXT, Code)", expanded=False):
    uploaded_file = st.file_uploader("Upload a file to add to context", type=["txt", "pdf", "csv", "py", "md"])

if user_input := st.chat_input("Ask anything..."):
    
    # Process attachment if exists
    if uploaded_file:
        with st.spinner("Processing file..."):
            file_content = process_uploaded_file(uploaded_file)
            user_input += f"\n\n[Attached File: {uploaded_file.name}]\n{file_content}\n"
            st.success(f"Attached {uploaded_file.name}")

    st.session_state.super_messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
    with st.chat_message("assistant"):
        # UI: Thinking Container
        st_callback = StreamlitCallbackHandler(st.container(), expand_new_thoughts=True)
        
        try:
            response = agent_executor.invoke(
                {"input": user_input},
                {"callbacks": [st_callback]}
            )
            output_text = response["output"]
            st.markdown(output_text, unsafe_allow_html=True)
            
            st.session_state.super_messages.append({"role": "assistant", "content": output_text})
        except Exception as e:
            st.error(f"Error: {e}")
