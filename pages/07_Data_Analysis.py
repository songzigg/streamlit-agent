import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os
import time

from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from langchain_classic.agents import AgentType
from utils import configure_api_key

st.set_page_config(page_title="Data Analysis", page_icon="📊")
st.header("📊 Data Analysis Assistant")

# 1. Configuration
deepseek_api_key = configure_api_key()

# 2. File Upload
uploaded_file = st.file_uploader("Upload Data (CSV or Excel)", type=["csv", "xlsx", "xls"])

# 3. Main Logic
if uploaded_file:
    # Load Data
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        st.write("### Data Preview")
        st.dataframe(df.head())
        
        # 4. Agent Setup
        llm = ChatOpenAI(
            model_name="deepseek-chat",
            openai_api_key=deepseek_api_key,
            openai_api_base="https://api.deepseek.com",
            temperature=0
        )
        
        # We use a custom prefix to instruct the agent about plotting
        prefix_prompt = """
        You are a Data Analysis Assistant. Working with the pandas dataframe `df`.
        
        RULES:
        1. If asked to plot/draw/chart:
           - Use matplotlib to generate the plot.
           - ALWAYS save the plot to a file named 'temp_plot.png'.
           - Do NOT use plt.show().
           - Return a final answer saying "I have generated the plot."
        2. For calculations, double check your code.
        """
        
        agent = create_pandas_dataframe_agent(
            llm, 
            df, 
            verbose=True,
            allow_dangerous_code=True,
            agent_executor_kwargs={"handle_parsing_errors": True}, # Fix for OutputParserException
            prefix=prefix_prompt
        )
        
        # 5. Chat Interface
        if "data_messages" not in st.session_state:
            st.session_state.data_messages = []
            
        for msg in st.session_state.data_messages:
            st.chat_message(msg["role"]).write(msg["content"])
            if msg.get("image"):
                st.image(msg["image"])
        
        if prompt := st.chat_input("Ask about your data..."):
            st.session_state.data_messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Analyzing..."):
                    # Clear old plot if exists
                    if os.path.exists("temp_plot.png"):
                        os.remove("temp_plot.png")
                        
                    try:
                        response = agent.invoke(prompt)
                        output_text = response["output"]
                        st.write(output_text)
                        
                        # Check for plot
                        image_path = None
                        if os.path.exists("temp_plot.png"):
                            st.image("temp_plot.png")
                            image_path = "temp_plot.png"
                        
                        st.session_state.data_messages.append({
                            "role": "assistant", 
                            "content": output_text,
                            "image": image_path
                        })
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
                        
    except Exception as e:
        st.error(f"Error reading file: {e}")
else:
    st.info("Please upload a CSV or Excel file to begin.")
