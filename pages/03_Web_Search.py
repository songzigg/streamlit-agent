import streamlit as st


from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
from langchain_openai import ChatOpenAI
from langchain_classic.agents import ConversationalChatAgent, AgentExecutor
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool

from langchain_community.utilities import SerpAPIWrapper
from utils import configure_api_key, configure_serpapi_key

st.set_page_config(page_title="Web Search", page_icon="🌍")
st.header("🌍 Autonomous Web Search Agent (SerpAPI)")

# 1. Configuration
deepseek_api_key = configure_api_key()
serpapi_api_key = configure_serpapi_key()

# 2. Setup Tools
search = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)

tools = [
    Tool(
        name="SerpAPI Search",
        func=search.run,
        description="Useful for when you need to answer questions about current events or specific facts that you don't know."
    )
]

# 3. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []

# Note: Agents handle memory a bit differently, often passing chat_history explicitly.
# But for simplicity in Streamlit, we can just use a buffer memory attached to the agent.
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="chat_history", 
        return_messages=True
    )

# 4. Agent Setup
llm = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    streaming=True
)

# Standard ReAct / Conversational Agent
# We use existing ConversationChatAgent from LangChain or create_react_agent
# For "Chat" capability + Tools, ConversationalChatAgent is good.
agent = ConversationalChatAgent.from_llm_and_tools(
    llm=llm, 
    tools=tools, 
    system_message="You are a helpful assistant with access to the internet. slightly adjust your tone to be professional yet engaging. Always verify information with search if you are unsure."
)

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent, 
    tools=tools, 
    verbose=True,
    memory=st.session_state.memory,
    handle_parsing_errors=True
)

# 5. Chat Interface
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

if prompt_input := st.chat_input("Ask me anything about the world..."):
    st.session_state.messages.append({"role": "user", "content": prompt_input})
    st.chat_message("user").write(prompt_input)

    with st.chat_message("assistant"):
        st_callback = StreamlitCallbackHandler(st.container())
        try:
            response = agent_executor.invoke(
                {"input": prompt_input}, 
                {"callbacks": [st_callback]}
            )
            output_text = response["output"]
            st.write(output_text)
            st.session_state.messages.append({"role": "assistant", "content": output_text})
        except Exception as e:
            st.error(f"Error during search execution: {e}")
