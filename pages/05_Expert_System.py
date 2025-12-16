import streamlit as st
import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA
from utils import configure_api_key

st.set_page_config(page_title="Expert System", page_icon="🎓")
st.header("🎓 Expert System (Persistent Knowledge Base)")

# 1. Configuration
deepseek_api_key = configure_api_key()
KB_FOLDER = "kb_index"

# 2. Setup Embeddings (Consistent model)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 3. Tabs for separation of concerns
tab1, tab2 = st.tabs(["🏗️ Knowledge Builder (Admin)", "💬 Expert Chat (User)"])

# --- TAB 1: Builder ---
with tab1:
    st.subheader("Knowledge Builder")
    st.info("Documents uploaded here will be saved to the permanent knowledge base.")
    
    uploaded_files = st.file_uploader("Upload Company Documents (PDF/TXT)", accept_multiple_files=True)
    
    if st.button("Add to Knowledge Base"):
        if uploaded_files:
            with st.spinner("Indexing documents..."):
                all_texts = []
                for uploaded_file in uploaded_files:
                    # Save temp
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_file_path = tmp_file.name
                    
                    try:
                        if uploaded_file.name.endswith(".pdf"):
                            loader = PyPDFLoader(tmp_file_path)
                        else:
                            loader = TextLoader(tmp_file_path)
                        docs = loader.load()
                        all_texts.extend(docs)
                    finally:
                        os.remove(tmp_file_path)
                
                # Split
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                splits = text_splitter.split_documents(all_texts)
                
                # Indexing
                if os.path.exists(KB_FOLDER):
                    # Load existing to append
                    # Note: Loading with allow_dangerous_deserialization=True is needed for recent FAISS versions if trusting local files
                    db = FAISS.load_local(KB_FOLDER, embeddings, allow_dangerous_deserialization=True)
                    db.add_documents(splits)
                else:
                    db = FAISS.from_documents(splits, embeddings)
                
                # Save
                db.save_local(KB_FOLDER)
                st.success(f"Successfully added {len(splits)} chunks to Knowledge Base!")
        else:
            st.warning("Please upload files first.")

# --- TAB 2: Chat ---
with tab2:
    st.subheader("Consult the Expert")
    
    if not os.path.exists(KB_FOLDER):
        st.warning("No Knowledge Base found. Please build it in the 'Knowledge Builder' tab first.")
    else:
        # Load DB
        try:
            db = FAISS.load_local(KB_FOLDER, embeddings, allow_dangerous_deserialization=True)
            
            # Chat Interface
            if "expert_messages" not in st.session_state:
                st.session_state.expert_messages = []
            
            for msg in st.session_state.expert_messages:
                st.chat_message(msg["role"]).write(msg["content"])
            
            if prompt := st.chat_input("Ask question based on the knowledge base..."):
                st.session_state.expert_messages.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Consulting Knowledge Base..."):
                        llm = ChatOpenAI(
                            model_name="deepseek-chat",
                            openai_api_key=deepseek_api_key,
                            openai_api_base="https://api.deepseek.com",
                            temperature=0.1
                        )
                        retriever = db.as_retriever(search_kwargs={"k": 4})
                        qa_chain = RetrievalQA.from_chain_type(
                            llm=llm,
                            chain_type="stuff",
                            retriever=retriever
                        )
                        
                        response = qa_chain.invoke({"query": prompt})
                        result = response["result"]
                        
                        st.write(result)
                        st.session_state.expert_messages.append({"role": "assistant", "content": result})
        except Exception as e:
            st.error(f"Error loading Knowledge Base: {e}")
