from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "EVUA Backend is running"}
