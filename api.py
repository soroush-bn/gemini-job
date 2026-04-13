import os
import threading
import json
import asyncio
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import existing pipeline components
from main import run_job_application_pipeline, get_response_text
from agents.job_finder.agent import get_job_finder_agent
from utils.messenger import pipeline_messenger
from config import JOBS_EVALUATED_DIR

app = FastAPI()

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Pass the running event loop to the messenger
    pipeline_messenger.set_loop(asyncio.get_running_loop())

@app.get("/jobs")
def get_evaluated_jobs():
    """Returns a list of folders in jobs_evaluated."""
    if not os.path.exists(JOBS_EVALUATED_DIR):
        return []
    return sorted(os.listdir(JOBS_EVALUATED_DIR), reverse=True)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async def send_updates():
        """Dedicated task to stream updates from the messenger to the client."""
        try:
            async for update in pipeline_messenger.get_updates():
                await websocket.send_text(update)
        except Exception as e:
            print(f"WS Send Error: {e}")

    # Start the sender task
    sender_task = asyncio.create_task(send_updates())
    
    try:
        while True:
            # Main loop for receiving commands from the client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "start_search":
                params = message["data"]
                thread = threading.Thread(
                    target=run_pipeline_flow, 
                    args=(params["role"], params["country"], params["work_type"])
                )
                thread.start()
            
            elif message["type"] == "process_url":
                url = message["data"]["url"]
                thread = threading.Thread(
                    target=run_job_application_pipeline,
                    args=(url,)
                )
                thread.start()

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        sender_task.cancel()

def run_pipeline_flow(role, country, work_type):
    """Orchestrates the job finder and subsequent pipeline runs."""
    pipeline_messenger.send("log", f"Initializing search for {role} in {country} ({work_type})...")
    
    agent = get_job_finder_agent()
    chat = agent.start_chat(enable_automatic_function_calling=True)
    
    # FORCED PROMPT: Prevents the agent from asking conversational questions.
    # It instructs the agent to perform the tool call IMMEDIATELY.
    prompt = (
        f"Search for {work_type} {role} jobs in {country}. "
        "I have provided all necessary details. Use the search_datanerd_jobs tool IMMEDIATELY. "
        "Do not ask me any follow-up questions. Return the results as a JSON list in a code block."
    )
    
    try:
        response = chat.send_message(prompt)
        text = get_response_text(response)
        
        pipeline_messenger.send("agent_chat", {"role": "agent", "content": text})
        
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0].strip()
            urls = json.loads(json_str)
            if isinstance(urls, list) and len(urls) > 0:
                pipeline_messenger.send("log", f"Found {len(urls)} jobs. Starting sequential pipeline processing...")
                for url in urls:
                    pipeline_messenger.send("log", f">>> BEGIN PROCESSING: {url}")
                    run_job_application_pipeline(url)
                pipeline_messenger.send("log", "SUCCESS: All discovered jobs have been processed.")
            else:
                pipeline_messenger.send("log", "Job Finder found 0 matching URLs.")
        else:
            pipeline_messenger.send("log", "Job Finder did not return a structured JSON list. Check agent logs.")
            
    except Exception as e:
        pipeline_messenger.send("log", f"Pipeline Flow Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
