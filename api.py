# api.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn
import json
import asyncio
from typing import List
import os
import atexit
from graph import build_graph
from langchain_core.messages import HumanMessage, SystemMessage
from session_context import set_session_id, get_session_id

# Initialize FastAPI app
app = FastAPI(title="Conversational Bot API")

# CORS middleware to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the agent graph
agent = build_graph()

# System prompt from main.py
from prompts import SYSTEM_PROMPT

# Track uploaded files for cleanup
uploaded_files: List[str] = []

# Files directory
FILES_DIR = Path(r"C:\Users\PAX\My Conversational Bot\Files")
FILES_DIR.mkdir(exist_ok=True)

# Cleanup function to delete uploaded files
def cleanup_files():
    """Delete all uploaded files on shutdown"""
    print("\n🧹 Cleaning up uploaded files...")
    for file_path in uploaded_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"   Deleted: {file_path}")
        except Exception as e:
            print(f"   Error deleting {file_path}: {e}")
    uploaded_files.clear()
    print("✅ Cleanup complete\n")

# Register cleanup function to run on shutdown
atexit.register(cleanup_files)

# Store conversation history per WebSocket connection
conversations = {}

@app.get("/")
async def read_root():
    """Serve the React frontend"""
    frontend_path = Path(__file__).parent / "frontend" / "dist" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Frontend not built. Run 'npm run build' in the frontend directory."}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), session_id: str = Form("default")):
    """
    Upload files to the Files directory in a session-specific subdirectory.
    For CSV/Excel files, automatically loads and summarizes the dataset.
    Returns list of uploaded file paths and dataset summaries.
    """
    from tools import load_dataset
    
    uploaded_paths = []
    dataset_summaries = []
    
    # Create session-specific directory
    session_dir = FILES_DIR / session_id
    session_dir.mkdir(exist_ok=True)
    
    for file in files:
        try:
            # Create safe filename in session directory
            file_path = session_dir / file.filename
            
            # Save file
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Track for cleanup
            file_path_str = str(file_path.absolute())
            uploaded_files.append(file_path_str)
            
            file_info = {
                "filename": file.filename,
                "path": file_path_str,
                "size": len(content)
            }
            
            # Auto-load dataset if CSV or Excel
            ext = Path(file.filename).suffix.lower()
            if ext in ['.csv', '.xls', '.xlsx']:
                load_result = load_dataset.func(file_path_str)
                if load_result.get("success"):
                    file_info["dataset_loaded"] = True
                    file_info["dataset_summary"] = load_result.get("summary")
                    dataset_summaries.append({
                        "filename": file.filename,
                        "summary": load_result.get("summary")
                    })
                    print(f"📊 Dataset loaded: {file.filename}")
                else:
                    file_info["dataset_loaded"] = False
                    file_info["dataset_error"] = load_result.get("error")
            
            uploaded_paths.append(file_info)
            print(f"📁 Uploaded: {file.filename} to session {session_id} ({len(content)} bytes)")
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading {file.filename}: {str(e)}")
    
    return {
        "success": True,
        "files": uploaded_paths,
        "dataset_summaries": dataset_summaries,
        "message": f"Successfully uploaded {len(uploaded_paths)} file(s)"
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default"):
    """
    WebSocket endpoint for streaming chat conversations
    Accepts session_id as a query parameter for session isolation
    """
    await websocket.accept()
    connection_id = id(websocket)
    
    # Initialize conversation history with system prompt
    conversations[connection_id] = [SystemMessage(content=SYSTEM_PROMPT)]
    
    print(f"🔌 WebSocket connected: {connection_id} (session: {session_id})")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            print(f"💬 User (session {session_id}): {user_message}")
            
            # Add user message to conversation history
            conversations[connection_id].append(HumanMessage(content=user_message))
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "user_message",
                "content": user_message
            })
            
            try:
                # Set session ID in context before invoking agent
                set_session_id(session_id)
                
                # Invoke agent with conversation history
                result = agent.invoke({"messages": conversations[connection_id]})
                
                # Get the final message
                final_msg = result["messages"][-1]
                
                # Extract content
                if hasattr(final_msg, 'content') and final_msg.content:
                    response_content = final_msg.content
                else:
                    response_content = str(final_msg)
                
                print(f"Agent (session {session_id}): {response_content}")
                
                # Update conversation history with agent response
                conversations[connection_id] = result["messages"]
                
                # Send complete response
                await websocket.send_json({
                    "type": "agent_message",
                    "content": response_content,
                    "done": True
                })
                
            except Exception as e:
                error_message = f"Error processing message: {str(e)}"
                print(f"❌ {error_message}")
                await websocket.send_json({
                    "type": "error",
                    "content": error_message
                })
    
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {connection_id}")
        # Clean up conversation history
        if connection_id in conversations:
            del conversations[connection_id]
    
    except Exception as e:
        print(f"❌ WebSocket error: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Connection error: {str(e)}"
            })
        except:
            pass

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "uploaded_files_count": len(uploaded_files)
    }

# Mount static files for the built React app
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

# Mount plots directory
plots_dir = Path(r"C:\Users\PAX\My Conversational Bot\frontend\public\plots")
plots_dir.mkdir(parents=True, exist_ok=True)
app.mount("/plots", StaticFiles(directory=plots_dir), name="plots")

if __name__ == "__main__":
    print("🚀 Starting Conversational Bot API...")
    print("📡 WebSocket endpoint: ws://localhost:8000/ws")
    print("📤 Upload endpoint: http://localhost:8000/upload")
    print("🏥 Health check: http://localhost:8000/health")
    print("\n" + "="*50 + "\n")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
