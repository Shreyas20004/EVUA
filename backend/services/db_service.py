# connection to mongo db

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME")]

def save_message(session_id: str, role: str, content: str):
    db.history.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {"role": role, "content": content}}},
        upsert=True
    )

def get_history(session_id: str):
    record = db.history.find_one({"session_id": session_id})
    return record["messages"] if record else []
