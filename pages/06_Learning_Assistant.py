import streamlit as st
import tempfile
import os
import json

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.utilities import SerpAPIWrapper
from utils import configure_api_key, configure_serpapi_key

st.set_page_config(page_title="Learning Assistant", page_icon="🎓")
st.header("🎓 Personal Learning Assistant")

# 1. Configuration
deepseek_api_key = configure_api_key()
# Optional: SerpAPI for web search
try:
    serpapi_api_key = configure_serpapi_key()
    search_tool = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)
    search_enabled = True
except:
    search_enabled = False

# 2. Session State for Vector Store
if "learning_db" not in st.session_state:
    st.session_state.learning_db = None

# 3. Sidebar: Context Setup
with st.sidebar:
    st.subheader("1. Knowledge Source")
    uploaded_file = st.file_uploader("Upload Textbook/Notes (PDF/TXT)", type=["pdf", "txt"])
    
    if uploaded_file and not st.session_state.learning_db:
        if st.button("Process Material"):
            with st.spinner("Digesting material..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name
                
                try:
                    if uploaded_file.name.endswith(".pdf"):
                        loader = PyPDFLoader(tmp_file_path)
                    else:
                        loader = TextLoader(tmp_file_path)
                    docs = loader.load()
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    splits = text_splitter.split_documents(docs)
                    
                    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                    st.session_state.learning_db = FAISS.from_documents(splits, embeddings)
                    st.success("Material Ready!")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    os.remove(tmp_file_path)
    
    if st.session_state.learning_db:
         if st.button("Clear Material"):
             st.session_state.learning_db = None
             st.rerun()

    st.subheader("2. Settings")
    enable_web = st.toggle("Enable Web Search for Extra Context", value=False, disabled=not search_enabled)
    if enable_web and not search_enabled:
        st.caption("Add SerpAPI Key to enable.")

# 4. Main Interface
tab1, tab2, tab3 = st.tabs(["💬 Tutor Chat", "📝 Quiz Generator", "🗂️ Flashcards"])

llm = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    temperature=0.3
)

# --- TAB 1: Chat ---
with tab1:
    st.subheader("Tutor Chat")
    if "tutor_messages" not in st.session_state:
        st.session_state.tutor_messages = []
        
    for msg in st.session_state.tutor_messages:
        st.chat_message(msg["role"]).write(msg["content"])
        
    if prompt := st.chat_input("Ask your tutor..."):
        st.session_state.tutor_messages.append({"role": "user", "content": prompt})
        st.chat_message("user").write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response_text = ""
                
                # Logic: Web Search -> RAG -> Pure LLM
                params = {}
                context_text = ""
                
                # 1. Search Context
                if enable_web and search_enabled:
                    try:
                        search_res = search_tool.run(prompt)
                        context_text += f"\n[Web Search Results]: {search_res}\n"
                    except Exception as e:
                        st.warning(f"Search failed: {e}")
                
                # 2. Document Context
                if st.session_state.learning_db:
                    retriever = st.session_state.learning_db.as_retriever(search_kwargs={"k": 3})
                    docs = retriever.invoke(prompt)
                    doc_text = "\n".join([d.page_content for d in docs])
                    context_text += f"\n[Document Context]: {doc_text}\n"
                
                # 3. Construct Prompt
                system_prompt = """You are a personalized Tutor. 
                Use the provided Context (Web or Documents) to answer the student's question.
                If the answer isn't in the context, use your general knowledge but mention that.
                Be encouraging and clear.
                """
                
                full_prompt = f"Context:\n{context_text}\n\nQuestion: {prompt}"
                
                messages = [
                    ("system", system_prompt),
                    ("human", full_prompt)
                ]
                
                res = llm.invoke(messages)
                response_text = res.content
                
                st.markdown(response_text)
                st.session_state.tutor_messages.append({"role": "assistant", "content": response_text})

# --- TAB 2: Quiz ---
with tab2:
    st.subheader("Quiz Generator")
    topic = st.text_input("Enter Topic for Quiz (or leave blank for general):")
    
    if st.button("Generate Quiz"):
        with st.spinner("Generating Questions..."):
            context = "General Knowledge"
            if st.session_state.learning_db:
                # Retrieve random chunks or specific topic chunks
                if topic:
                    retriever = st.session_state.learning_db.as_retriever(search_kwargs={"k": 5})
                    docs = retriever.invoke(topic)
                    context = "\n".join([d.page_content for d in docs])
                else:
                    # just take some random text? Facade: just ask LLM to generate based on "Uploaded Material" concept
                    # Ideally we need to sample the DB, but for now let's query with "Summary"
                    retriever = st.session_state.learning_db.as_retriever(search_kwargs={"k": 5})
                    docs = retriever.invoke("Key concepts of this document")
                    context = "\n".join([d.page_content for d in docs])
            
            # JSON Output Parser
            quiz_prompt = ChatPromptTemplate.from_template(
                """Generate 5 multiple-choice questions based ONLY on the following context.
                
                Context: {context}
                
                Return the output as a valid JSON list of objects. Each object should have:
                - "question": string
                - "options": list of 4 strings
                - "answer": string (must be one of the options)
                - "explanation": string
                
                Ensure valid JSON. No markdown ticks.
                """
            )
            
            chain = quiz_prompt | llm | JsonOutputParser()
            
            try:
                quiz_data = chain.invoke({"context": context})
                st.session_state.quiz_data = quiz_data
            except Exception as e:
                st.error(f"Failed to generate quiz: {e}")
    
    # Render Quiz
    if "quiz_data" in st.session_state:
        score = 0
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Q{i+1}: {q['question']}**")
            user_choice = st.radio(f"Select answer for Q{i+1}", q['options'], key=f"q_{i}")
            
            if st.button(f"Check Q{i+1}", key=f"btn_{i}"):
                if user_choice == q['answer']:
                    st.success("Correct!")
                else:
                    st.error(f"Wrong. Correct: {q['answer']}")
                st.info(f"Why: {q['explanation']}")
            st.markdown("---")

# --- TAB 3: Flashcards ---
with tab3:
    st.subheader("Flashcards")
    if st.button("Generate Flashcards"):
        if st.session_state.learning_db:
             with st.spinner("Summarizing key terms..."):
                retriever = st.session_state.learning_db.as_retriever(search_kwargs={"k": 5})
                docs = retriever.invoke("Important definitions and terms")
                context = "\n".join([d.page_content for d in docs])
                
                flashcard_prompt = ChatPromptTemplate.from_template(
                    """Identify 5 key terms/concepts from the context.
                    Return a JSON list with:
                    - "term": string
                    - "definition": string (concise)
                    
                    Context: {context}
                    """
                )
                chain = flashcard_prompt | llm | JsonOutputParser()
                try:
                    cards = chain.invoke({"context": context})
                    
                    cols = st.columns(3)
                    for i, card in enumerate(cards):
                        with cols[i % 3]:
                            with st.expander(f"📇 {card['term']}", expanded=True):
                                st.write(card['definition'])
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Upload material first.")
