# Streamlit AI Agent Suite 🤖

A comprehensive AI application suite built with Streamlit and LangChain, featuring DeepSeek LLM integration. This project demonstrates a wide range of agentic workflows, from simple chatbots to autonomous research agents and Model Context Protocol (MCP) integration.

## 🌟 Features

### Core Modules
1.  **💬 Intelligent Chatbot**: Multi-turn conversation with memory, powered by DeepSeek.
2.  **📄 Document Q&A**: RAG (Retrieval Augmented Generation) system for querying PDF/TXT files.
3.  **🌐 Web Search Agent**: Autonomous agent capable of searching the internet via SerpAPI.
4.  **🛠️ Text Analysis Tools**: Entity extraction, sentiment analysis, and translation/polishing.
5.  **🧠 Expert System**: Persistent knowledge base management using FAISS/Chroma.

### Vertical Applications
6.  **📚 Learning Assistant**: Personal tutor with quiz generation and flashcards.
7.  **📊 Data Analysis**: Natural language data analysis and plotting for CSV/Excel files (Pandas Agent).
8.  **🕵️‍♂️ Research Agent**: Autonomous Planner-Researcher-Writer system for generating deep research reports.
9.  **🎛️ MCP Control Center**: Manage Model Context Protocol servers, tools, and context injection.

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- [DeepSeek API Key](https://platform.deepseek.com/)
- [SerpAPI Key](https://serpapi.com/) (Optional, for Search & Research)
- Node.js & `npx` (Optional, for MCP Filesystem server)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd streamlit-agent
    ```

2.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Copy `.env.example` to `.env` and fill in your API keys:
    ```bash
    cp .env.example .env
    ```
    *Alternatively, you can enter API keys directly in the Streamlit Sidebar.*

### Running the App

```bash
streamlit run Home.py
```

Visit `http://localhost:8501` in your browser.

## 📂 Project Structure

```
├── Home.py                 # Main application entry point
├── pages/                  # Streamlit pages (Individual Features)
│   ├── 01_Chatbot.py
│   ├── 02_Document_QA.py
│   ├── 03_Web_Search.py
│   ├── 04_Text_Analysis.py
│   ├── 05_Expert_System.py
│   ├── 06_Learning_Assistant.py
│   ├── 07_Data_Analysis.py
│   ├── 08_Research_Agent.py
│   └── 09_MCP_Control_Center.py
├── utils.py                # Shared utilities
├── requirements.txt        # Python Dependencies
├── mcp_config.json         # MCP Server configuration
└── .env                    # Secrets (Ignored by Git)
```

## 🛠️ Technologies
- **Frontend**: [Streamlit](https://streamlit.io/)
- **LLM Framework**: [LangChain](https://python.langchain.com/)
- **Models**: DeepSeek V3 (via OpenAI compatibility)
- **Vector Store**: FAISS
- **Search**: SerpAPI
- **Agents**: LangChain Agents, Model Context Protocol (MCP)

## 📜 License
MIT
