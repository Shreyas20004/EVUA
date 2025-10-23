from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import llm.models
from services.llm_service import query_ollama
from services.db_service import save_message, get_history
import uuid
from typing import Optional
app = FastAPI()

# CORS (for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Code Upgrade Assistant API"}
@app.post("/api/upgrade")
async def upgrade_code(
    model: str = Form(...),
    file: Optional[UploadFile] = None,
    session_id: str = Form(default=None)
):
    session_id = session_id or str(uuid.uuid4())
    system_prompt = "You are a coding assistant for a project upgrade tool. Help the user refactor, debug, or improve their code. Be concise but detailed when needed."
    if file is None:
        return {"error": "No file uploaded"}
    
    input_data = await file.read()
    input_text = input_data.decode("utf-8")

    history = get_history(session_id)
    response = query_ollama(model, system_prompt, input_text, history)

    save_message(session_id, "user", input_text)
    save_message(session_id, "assistant", response)

    return {"session_id": session_id, "response": response}


@app.post("/api/chat")
async def chat_with_llm(model: str = Form(...), user_input: str = Form(...), session_id: str = Form(default=None)):
    session_id = session_id or str(uuid.uuid4())
    history = get_history(session_id)

    system_prompt = (
        "You are an advanced AI coding assistant, similar to GitHub Copilot. "
        "When given code, first detect the programming language automatically. "
        "Upgrade the code to the latest stable version of the language and its frameworks, "
        "refactor for best practices, and resolve any deprecated or outdated syntax. "
        "Check for dependency issues and suggest or apply necessary updates. "
        "Always preserve the original logic and intent. "
        "Be concise, accurate, and provide only the improved code unless further explanation is requested."
    )
    
    response = query_ollama(model, system_prompt, user_input, history)
    save_message(session_id, "user", user_input)
    save_message(session_id, "assistant", response)

    return {"session_id": session_id, "response": response}


@app.get("/api/history/{session_id}")
async def fetch_history(session_id: str):
    return {"session_id": session_id, "history": get_history(session_id)}


@app.get("/api/models")
async def list_models():
    # Return a list of available Ollama models
    models = llm.models.get_available_models()
    return {"models": models}
