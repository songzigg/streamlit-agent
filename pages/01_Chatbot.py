import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_classic.memory import ConversationBufferMemory
from langchain_classic.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from langchain_core.messages import HumanMessage, AIMessage
from utils import configure_api_key

st.set_page_config(page_title="DeepSeek Chatbot", page_icon="🤖")
st.header("🤖 DeepSeek Chatbot")

# 1. Configuration
# We reuse the OpenAI client but point it to DeepSeek's API
deepseek_api_key = configure_api_key()

with st.sidebar:
    st.header("Settings")
    model_name = st.selectbox(
        "Select Model",
        options=["deepseek-chat", "deepseek-coder"],
        index=0
    )
    system_prompt = st.text_area(
        "System Prompt (Role)",
        value="You are a helpful AI assistant.",
        help="Define how the AI should behave."
    )
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.memory.clear()
        st.rerun()

# 2. State Management
if "messages" not in st.session_state:
    st.session_state.messages = []

if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(return_messages=True)

# 3. LangChain Setup
# DeepSeek is OpenAI compatible
llm = ChatOpenAI(
    model_name=model_name,
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    streaming=True
)

# Custom Prompt
prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(system_prompt),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ]
)

chain = LLMChain(
    llm=llm,
    prompt=prompt,
    memory=st.session_state.memory,
    verbose=True
)

# 4. Chat Interface
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    else:
        st.chat_message("assistant").write(msg["content"])

if user_input := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)
    
    # Check for MCP Context
    mcp_context_str = ""
    if "context_context" in st.session_state and st.session_state.context_context:
        mcp_context_str = "\n\n[Active Memory Context]:\n"
        for item in st.session_state.context_context:
            mcp_context_str += f"-- Source: {item['source']} --\n{item['content']}\n"
        mcp_context_str += "\n[End Context]\n"

    # Construct full prompt with history
    history_langchain_format = []
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            # Inject context only into the latest message effectively
            content = msg["content"]
            if msg == st.session_state.messages[-1] and mcp_context_str:
                content += mcp_context_str
            history_langchain_format.append(HumanMessage(content=content))
        elif msg["role"] == "assistant":
            history_langchain_format.append(AIMessage(content=msg["content"]))
    
    with st.chat_message("assistant"):
        chat_container = st.empty()
        try:
            # Prepare chain
            chain = prompt | llm
            
            # Stream response
            response_text = ""
            for chunk in chain.stream({
                "history": history_langchain_format[:-1], # Pass history excluding current
                "input": history_langchain_format[-1].content # Current input with context
            }):
                response_text += chunk.content
                chat_container.markdown(response_text)
            
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        except Exception as e:
            st.error(f"Error: {e}")
