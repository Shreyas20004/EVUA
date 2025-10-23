from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

def test_mongodb_connection(uri="mongodb://localhost:27017/"):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        print("MongoDB connection successful.")
    except ConnectionFailure as e:
        print(f"MongoDB connection failed: {e}")

if __name__ == "__main__":
    test_mongodb_connection()