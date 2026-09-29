from fastapi import FastAPI
from app.routes import upload, translate, review
from fastapi.middleware.cors import CORSMiddleware
from app.database.database import Base, engine
from app.database import models


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Multilingual Document Translation API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(translate.router)
app.include_router(review.router)

@app.get("/")
def root():
    return {
        "message": "Backend is running successfully!"
    }