# api.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List
import os
import json
import atexit

# --- Project imports ---
from graph import build_graph
from langchain_core.messages import HumanMessage, SystemMessage
from session_context import set_session_id, get_session_id
from prompts import SYSTEM_PROMPT

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    # Audio
    '.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac',
    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
    # Data
    '.csv', '.xls', '.xlsx'
}

# Initialize FastAPI app
app = FastAPI(title="Conversational Bot API")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# --- Agent setup ---
agent = build_graph()

# --- Track uploaded files ---
uploaded_files: List[str] = []

# --- File directories (relative paths for Railway) ---
FILES_DIR = Path(__file__).parent / "Files"
FILES_DIR.mkdir(exist_ok=True)

plots_dir = Path(__file__).parent / "frontend" / "public" / "plots"
plots_dir.mkdir(parents=True, exist_ok=True)

# --- Cleanup on shutdown ---
def cleanup_files():
    print("\n🧹 Cleaning up uploaded files...")
    directories_to_clean = set()
    for file_path in uploaded_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"   Deleted: {file_path}")
                directories_to_clean.add(os.path.dirname(file_path))
        except Exception as e:
            print(f"   Error deleting {file_path}: {e}")
    
    # Try to remove session directories if empty
    for dir_path in directories_to_clean:
        try:
            if os.path.exists(dir_path):
                os.rmdir(dir_path)
                print(f"   Deleted folder: {dir_path}")
        except OSError:
            # Directory not empty or other OS error
            pass
        except Exception as e:
            print(f"   Error deleting folder {dir_path}: {e}")

    uploaded_files.clear()
    print("✅ Cleanup complete\n")

atexit.register(cleanup_files)

# --- Conversation tracking ---
conversations = {}

# --- React frontend paths ---
frontend_dist = Path(__file__).parent / "frontend" / "dist"

# Mount static assets
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

# Mount plots
app.mount("/plots", StaticFiles(directory=plots_dir), name="plots")

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "uploaded_files_count": len(uploaded_files)
    }

@app.get("/")
async def serve_root():
    """Serve React frontend index.html"""
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built. Run 'npm run build' in the frontend directory."}

# Catch-all route for React SPA routing
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Frontend not built"}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...), session_id: str = Form("default")):
    """Upload files, auto-load CSV/Excel datasets, return summaries"""
    from tools import load_dataset

    uploaded_paths = []
    dataset_summaries = []
    
    # Notification message builder
    notification_content = f"User uploaded {len(files)} file(s):\n"

    session_dir = FILES_DIR / session_id
    session_dir.mkdir(exist_ok=True)

    for file in files:
        try:
            file_path = session_dir / file.filename
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type not allowed: {file.filename}. Allowed: Audio, Images, CSV/Excel"
                )

            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            uploaded_files.append(str(file_path.absolute()))

            file_info = {
                "filename": file.filename,
                "path": str(file_path.absolute()),
                "size": len(content)
            }

            # Auto-load dataset
            if ext in ['.csv', '.xls', '.xlsx']:
                load_result = load_dataset.func(str(file_path))
                if load_result.get("success"):
                    file_info["dataset_loaded"] = True
                    file_info["dataset_summary"] = load_result.get("summary")
                    dataset_summaries.append({
                        "filename": file.filename,
                        "summary": load_result.get("summary")
                    })
                else:
                    file_info["dataset_loaded"] = False
                    file_info["dataset_error"] = load_result.get("error")

            uploaded_paths.append(file_info)
            uploaded_paths.append(file_info)
            notification_content += f"- {file.filename} ({len(content)} bytes)\n"
            print(f"📁 Uploaded: {file.filename} to session {session_id} ({len(content)} bytes)")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading {file.filename}: {str(e)}")

        if dataset_summaries:
            notification_content += "\nDataset Summaries:\n" + "\n".join([f"- {s['filename']}: {s['summary']}" for s in dataset_summaries])

        # Notify agent
        if session_id not in conversations:
             conversations[session_id] = [SystemMessage(content=SYSTEM_PROMPT)]
        
        conversations[session_id].append(SystemMessage(content=notification_content))
        print(f"🔔 Notified session {session_id} about uploads")

    return {
        "success": True,
        "files": uploaded_paths,
        "dataset_summaries": dataset_summaries,
        "message": f"Successfully uploaded {len(uploaded_paths)} file(s)"
    }

# --- WebSocket endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default"):
    await websocket.accept()
    connection_id = id(websocket)
    
    # Initialize session if needed
    if session_id not in conversations:
        conversations[session_id] = [SystemMessage(content=SYSTEM_PROMPT)]
        
    print(f"🔌 WebSocket connected: {connection_id} (session: {session_id})")

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")

            if not user_message:
                continue

            # Append user message to session history
            conversations[session_id].append(HumanMessage(content=user_message))

            # Acknowledge user message
            await websocket.send_json({"type": "user_message", "content": user_message})

            try:
                set_session_id(session_id)
                final_state = None
                
                # Use session history for generation
                async for event in agent.astream_events({"messages": conversations[session_id]}, version="v2"):
                    kind = event["event"]

                    if kind == "on_chat_model_stream":
                        content = event["data"]["chunk"].content
                        if content:
                            await websocket.send_json({"type": "token", "content": content})

                    if kind == "on_chain_end" and event["name"] == "LangGraph":
                        final_state = event["data"]["output"]

                # Update conversation history with agent response
                if final_state and "messages" in final_state:
                    conversations[session_id] = final_state["messages"]

                # Send done message
                await websocket.send_json({"type": "agent_message", "content": "", "done": True})

            except Exception as e:
                await websocket.send_json({"type": "error", "content": f"Error processing message: {str(e)}"})

    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected: {connection_id}")
        # data = await websocket.receive_text()
        # Do NOT remove conversation history on disconnect to allow persistence
        pass
    except Exception as e:
        print(f"❌ WebSocket error: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "content": f"Connection error: {str(e)}"})
        except:
            pass

# --- Run app ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting API on port {port}...")
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False, log_level="info")
