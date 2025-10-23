# connection to mongo db

from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# Get environment variables with fallback values
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
db_name = os.getenv("DB_NAME", "evua_db")

client = MongoClient(mongo_uri)
db = client[db_name]

def save_message(session_id: str, role: str, content: str):
    db.history.update_one(
        {"session_id": session_id},
        {"$push": {"messages": {"role": role, "content": content}}},
        upsert=True
    )

def get_history(session_id: str):
    record = db.history.find_one({"session_id": session_id})
    return record["messages"] if record else []
