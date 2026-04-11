from langchain_google_genai import ChatGoogleGenerativeAI
from config import PRIMARY_MODEL
import os

SUPERVISOR_PROMPT = """You are a strict routing supervisor managing a job application pipeline. 
Read the conversation history and decide who should act next.

Available Routing Options:
- JOB_READER: If the user provides a URL and it hasn't been read/summarized yet.
- COMPANY_RESEARCHER: If the job description HAS been summarized, but we haven't researched the company's culture and projects yet.
- ANDROID_TAILOR: If BOTH the job description AND the company research have been completed, and it's time to tailor the CV.
- FINISH: If the CV has been successfully tailored and compiled to a PDF.

CRITICAL INSTRUCTION: Your entire response must be EXACTLY ONE WORD from the options above. Do not add punctuation, do not add pleasantries, and do not ask follow-up questions."""

def create_supervisor_node():
    llm = ChatGoogleGenerativeAI(model=PRIMARY_MODEL, api_key=os.getenv("GEMINI_API_KEY"))
    
    def node_function(state):
        messages = [{"role": "system", "content": SUPERVISOR_PROMPT}] + state["messages"]
        response = llm.invoke(messages)
        
        # 1. Get the raw text from Gemini and make it uppercase
        raw_text = response.content.strip().upper()
        
        # 2. Safety Net: Even if Gemini gets chatty, we search the text for our keywords
        next_node = "FINISH" # Default to finish if it breaks
        
        if "JOB_READER" in raw_text:
            next_node = "JOB_READER"
        elif "COMPANY_RESEARCHER" in raw_text:
            next_node = "COMPANY_RESEARCHER"
        elif "ANDROID_TAILOR" in raw_text:
            next_node = "ANDROID_TAILOR"
            
        # Return the clean routing command alongside the message
        return {"next_node": next_node, "messages": [response]}
        
    return node_function