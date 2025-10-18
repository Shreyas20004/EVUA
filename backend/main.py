from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from services.llm_service import query_ollama
from services.db_service import save_message, get_history
import uuid

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
    system_prompt: str = Form(...),
    file: UploadFile = None,
    session_id: str = Form(default=None)
):
    session_id = session_id or str(uuid.uuid4())
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

    system_prompt = """You are a coding assistant for a project upgrade tool.
    Help the user refactor, debug, or improve their code. Be concise but detailed when needed."""
    
    response = query_ollama(model, system_prompt, user_input, history)

    save_message(session_id, "user", user_input)
    save_message(session_id, "assistant", response)

    return {"session_id": session_id, "response": response}


@app.get("/api/history/{session_id}")
async def fetch_history(session_id: str):
    return {"session_id": session_id, "history": get_history(session_id)}


