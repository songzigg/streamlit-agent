import streamlit as st
import json
import time

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.utilities import SerpAPIWrapper
from utils import configure_api_key, configure_serpapi_key

st.set_page_config(page_title="Research Agent", page_icon="🕵️‍♂️")
st.header("🕵️‍♂️ Autonomous Research Agent")

# 1. Configuration
deepseek_api_key = configure_api_key()
try:
    serpapi_api_key = configure_serpapi_key()
    search = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)
    search_enabled = True
except:
    st.error("SerpAPI Key is required for this agent. Please set it in the sidebar.")
    search_enabled = False

# 2. LLM Setup
llm = ChatOpenAI(
    model_name="deepseek-chat",
    openai_api_key=deepseek_api_key,
    openai_api_base="https://api.deepseek.com",
    temperature=0.4
)

# 3. Chains
# --- Planner ---
planner_prompt = ChatPromptTemplate.from_template(
    """You are a Research Planning Agent.
    Topic: {topic}
    
    Break this topic down into 3-5 specific, google-able research questions that will help write a comprehensive report.
    Return the result as a JSON list of strings.
    Example: ["What is the market size of X?", "Key challenges in Y", "Recent regulations in Z"]
    """
)
planner_chain = planner_prompt | llm | JsonOutputParser()

# --- Summarizer ---
summarizer_prompt = ChatPromptTemplate.from_template(
    """You are a Research Assistant.
    Research Question: {question}
    Search Results: {results}
    
    Synthesize these search results into a concise summary of key facts, statistics, and insights relevant to the question.
    Cite the source index like [1], [2] if possible.
    """
)
summarizer_chain = summarizer_prompt | llm | StrOutputParser()

# --- Writer ---
writer_prompt = ChatPromptTemplate.from_template(
    """You are a Professional Report Writer.
    Topic: {topic}
    Structure the report with:
    - Title
    - Executive Summary
    - Detailed Sections (based on research)
    - Conclusion
    - References (list the sources mentioned)
    
    Research Data:
    {research_data}
    
    Write the final report in Markdown format.
    """
)
writer_chain = writer_prompt | llm | StrOutputParser()

# 4. UI
with st.sidebar:
    st.info("Input a broad topic, and the Agent will plan, search, and write a report for you.")

topic = st.text_input("Enter Research Topic:", placeholder="e.g. The Future of Solid State Batteries")

if st.button("Start Research") and search_enabled and topic:
    final_report = ""
    research_log = []
    
    # CONTAINER for updates
    status_container = st.status("🕵️‍♂️ Agent Working...", expanded=True)
    
    try:
        # Step 1: Planning
        status_container.write("🧠 Planning research strategy...")
        plan = planner_chain.invoke({"topic": topic})
        status_container.write(f"✅ Generated Plan: {plan}")
        
        # Step 2: Research Loop
        aggregated_findings = ""
        
        for i, question in enumerate(plan):
            status_container.write(f"🌐 Researching Step {i+1}/{len(plan)}: {question}")
            
            # Execute Search
            try:
                # SerpAPIWrapper's run method returns a string summary usually
                results = search.run(question)
                
                # Expand on results if they are too short? Not strictly needed with SerpAPI summary
                # Let's synthesize it
                summary = summarizer_chain.invoke({"question": question, "results": results})
                
                aggregated_findings += f"\n\n### Question: {question}\n{summary}\n"
                status_container.write(f"📝 Findings for Q{i+1} recorded.")
                time.sleep(1) # Be nice to API rates
                
            except Exception as e:
                status_container.error(f"Search failed for '{question}': {e}")
        
        # Step 3: Writing
        status_container.write("✍️ Writing final report...")
        final_report = writer_chain.invoke({"topic": topic, "research_data": aggregated_findings})
        status_container.update(label="✅ Research Complete!", state="complete", expanded=False)
        
        # Display
        st.divider()
        st.subheader("Final Report")
        st.markdown(final_report)
        
        # Download
        st.download_button(
            label="Download Report (Markdown)",
            data=final_report,
            file_name=f"Report_{topic.replace(' ', '_')}.md",
            mime="text/markdown"
        )
        
    except Exception as e:
        status_container.update(label="❌ Error occurred", state="error")
        st.error(f"An error occurred: {e}")
