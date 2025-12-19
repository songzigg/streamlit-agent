import streamlit as st

st.set_page_config(
    page_title="LangChain + Streamlit Agent",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Agent Playground")

st.markdown("""
### Welcome to your AI Agent Command Center!

This application demonstrates the power of **LangChain** combined with **Streamlit** to build interactive AI applications.

#### 👈 Select a Module from the Sidebar

**Available Modules:**

1.  **💬 Intelligent Chatbot**: 
    - Capabilities: Multi-turn conversation, Memory, System Prompt customization.
    - Status: *Ready*
2.  **📄 Document Q&A**: 
    - Capabilities: PDF/TXT Support, Local Embeddings, Source Citations.
    - Status: *Ready*
3.  **🔎 Web Search**:
    - Capabilities: Autonomous Internet Access, Current Events.
    - Status: *Ready*
4.  **🧠 Tools & Analysis**:
    - Capabilities: Entity Extraction, Sentiment Analysis, Translation.
    - Status: *Ready*
5.  **🎓 Expert System**:
    - Capabilities: Persistent Knowledge Base, Admin Mode.
    - Status: *Ready*
6.  **📚 Learning Assistant**:
    - Capabilities: Hybrid RAG+Search, Quizzes, Flashcards.
    - Status: *Ready*
7.  **📊 Data Analysis**:
    - Capabilities: CSV/Excel, Natural Language Queries, Plotting.
    - Status: *Ready*
8.  **🕵️‍♂️ Research Agent**:
    - Capabilities: Autonomous Internet Research, Report Generation.
    - Status: *Ready*
9.  **🎛️ MCP Control Center**:
    - Capabilities: Manage Servers, Inject Context, Run Tools.
    - Status: *Ready*
10. **🦸‍♂️ Super Chat**:
    - Capabilities: Unified Agent, Web Search, Image Gen, Memory.
    - Status: *Live!*

---
*Built with [Streamlit](https://streamlit.io) and [LangChain](https://python.langchain.com/)* 
""")
