import os
import streamlit as st
from dotenv import load_dotenv

def configure_api_key():
    load_dotenv()
    # Check for DeepSeek key first, then fall back to others if needed in future
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if not api_key:
        api_key = st.sidebar.text_input(
            "DeepSeek API Key", 
            type="password",
            help="Get your API key from https://platform.deepseek.com/"
        )
        if not api_key:
            st.warning("Please add your DeepSeek API key to continue.")
            st.stop()
            
    return api_key

def configure_serpapi_key():
    load_dotenv()
    api_key = os.getenv("SERPAPI_API_KEY")
    
    if not api_key:
        api_key = st.sidebar.text_input(
            "SerpAPI API Key", 
            type="password",
            help="Get your API key from https://serpapi.com/"
        )
        if not api_key:
            st.warning("Please add your SerpAPI API key to continue.")
            st.stop()
            
    return api_key

def sidebar_bg(side_bg):
   side_bg_ext = 'png'
   st.markdown(
      f"""
      <style>
      [data-testid="stSidebar"] > div:first-child {{
          background: url(data:image/{side_bg_ext};base64,{side_bg});
      }}
      </style>
      """,
      unsafe_allow_html=True,
      )
