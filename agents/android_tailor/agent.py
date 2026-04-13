from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from .skills.cv_tools import read_latex_cv, save_tailored_latex_cv, compile_latex_to_pdf
from .prompt import SYSTEM_PROMPT
from config import MODEL_NAME
import os

def create_android_tailor_node():
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, api_key=os.getenv("GEMINI_API_KEY"))
    
    # Give it all three tools
    tool_agent = create_react_agent(llm, tools=[read_latex_cv, save_tailored_latex_cv, compile_latex_to_pdf], prompt=SYSTEM_PROMPT)
    
    def node_function(state):
        result = tool_agent.invoke({"messages": state["messages"]})
        new_messages = result["messages"][len(state["messages"]):]
        return {"messages": new_messages}
        
    return node_function