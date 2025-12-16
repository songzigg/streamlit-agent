import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from utils import configure_api_key

st.set_page_config(page_title="Text Analysis", page_icon="🧠")
st.header("🧠 Intelligent Text Analysis (DeepSeek)")

# 1. Configuration
deepseek_api_key = configure_api_key()

# 2. LLM Setup
llm = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    temperature=0  # Low temperature for analysis tasks
)

# 3. Tabs
tab1, tab2, tab3 = st.tabs(["📝 Entity Extraction", "😊 Sentiment Analysis", "🌐 Translation & Polishing"])

# --- TAB 1: Entity Extraction ---
with tab1:
    st.subheader("Entity Extraction")
    text_input_ner = st.text_area("Enter text to extract entities from:", height=150, key="ner_input")
    
    if st.button("Extract Entities"):
        if text_input_ner:
            with st.spinner("Extracting..."):
                prompt = ChatPromptTemplate.from_template(
                    """Assuming the role of an expert data analyst.
                    Extract the following entities from the text below:
                    - Persons (Name)
                    - Organizations (Company, Institution)
                    - Locations (City, Country)
                    - Dates/Time
                    
                    Format the output as a Markdown table. If no entities are found, say "No entities found."
                    
                    Text: {text}
                    """
                )
                chain = prompt | llm | StrOutputParser()
                result = chain.invoke({"text": text_input_ner})
                st.markdown(result)
        else:
            st.warning("Please enter some text.")

# --- TAB 2: Sentiment Analysis ---
with tab2:
    st.subheader("Sentiment Analysis")
    text_input_sentiment = st.text_area("Enter text to analyze sentiment:", height=150, key="sentiment_input")
    
    if st.button("Analyze Sentiment"):
        if text_input_sentiment:
            with st.spinner("Analyzing..."):
                prompt = ChatPromptTemplate.from_template(
                    """Analyze the sentiment of the following text.
                    Classify it as Positive, Negative, or Neutral.
                    Provide a brief explanation for your classification.
                    
                    Output format:
                    **Sentiment**: [Class]
                    **Reasoning**: [Explanation]
                    
                    Text: {text}
                    """
                )
                chain = prompt | llm | StrOutputParser()
                result = chain.invoke({"text": text_input_sentiment})
                st.success("Analysis Complete")
                st.markdown(result)
        else:
            st.warning("Please enter some text.")

# --- TAB 3: Translation & Polishing ---
with tab3:
    st.subheader("Translation & Polishing")
    
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("Select Mode", ["Translate", "Polish/Rewrite"])
    with col2:
        target_lang = st.selectbox("Target Language (if Translating)", ["English", "Chinese", "Japanese", "French", "German"])
        
    text_input_trans = st.text_area("Enter text:", height=150, key="trans_input")
    
    if st.button("Generate"):
        if text_input_trans:
            with st.spinner("Processing..."):
                if mode == "Translate":
                    template = "Translate the following text to {lang}. Ensure the tone is natural and accurate.\n\nText: {text}"
                    variables = {"lang": target_lang, "text": text_input_trans}
                else:
                    template = "Polish the following text to be more professional, clear, and engaging. Fix any grammar errors.\n\nText: {text}"
                    variables = {"text": text_input_trans} # Lang variable unused for polish, but prompt template needs to match
                
                # Dynamic construction
                prompt = ChatPromptTemplate.from_template(template)
                chain = prompt | llm | StrOutputParser()
                
                result = chain.invoke(variables)
                st.markdown("### Result:")
                st.markdown(result)
        else:
            st.warning("Please enter some text.")
