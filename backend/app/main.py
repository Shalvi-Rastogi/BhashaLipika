from fastapi import FastAPI
from app.routes import upload

app = FastAPI(
    title="Multilingual Document Translation API",
    version="1.0.0"
)

app.include_router(upload.router)

@app.get("/")
def root():
    return {
        "message": "Backend is running successfully!"
    }