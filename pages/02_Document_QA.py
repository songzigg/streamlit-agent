import streamlit as st
import tempfile
import os

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_classic.chains import RetrievalQA
from utils import configure_api_key

st.set_page_config(page_title="Document Q&A", page_icon="📄")
st.header("📄 Chat with your Documents")

# 1. Configuration
deepseek_api_key = configure_api_key()

# 2. File Upload
uploaded_file = st.file_uploader("Upload a PDF or TXT file", type=["pdf", "txt"])

if uploaded_file:
    # Save uploaded file to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    st.success(f"File uploaded: {uploaded_file.name}")

    if st.button("Process Document"):
        with st.spinner("Processing document... (This may take a moment needed for embeddings)"):
            try:
                # Loader Selection
                if uploaded_file.name.endswith(".pdf"):
                    loader = PyPDFLoader(tmp_file_path)
                else:
                    loader = TextLoader(tmp_file_path)
                
                documents = loader.load()

                # Split Text
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                texts = text_splitter.split_documents(documents)
                st.info(f"Split into {len(texts)} chunks.")

                # Create Vector Store (Local Embeddings)
                # Using a small, fast model
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                
                # Create VectorStore
                db = FAISS.from_documents(texts, embeddings)
                
                # Store in session state
                st.session_state.db = db
                st.success("Document processed and indexed!")
            except Exception as e:
                st.error(f"Error processing file: {e}")
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)

# 3. Q&A Interface
if "db" in st.session_state:
    st.markdown("---")
    query = st.text_input("Ask a question about your document:")
    
    if query:
        with st.spinner("Thinking..."):
            # Setup Retriever
            retriever = st.session_state.db.as_retriever(search_kwargs={"k": 3})
            
            # Setup LLM (DeepSeek)
            llm = ChatOpenAI(
                model_name="deepseek-chat",
                openai_api_key=deepseek_api_key,
                openai_api_base="https://api.deepseek.com",
                temperature=0.2
            )
            
            # Setup Chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            # Execute
            result = qa_chain.invoke({"query": query})
            
            st.markdown(f"### Answer:\n{result['result']}")
            
            # Show sources
            with st.expander("View Source Documents"):
                for i, doc in enumerate(result["source_documents"]):
                    st.markdown(f"**Source {i+1}:**")
                    st.text(doc.page_content)
else:
    st.info("Please upload and process a document to start chatting.")
