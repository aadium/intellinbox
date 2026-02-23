from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import models
from database import engine
from routes import emails, inboxes
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="IntellInbox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(emails.router)
app.include_router(inboxes.router)

@app.get("/")
def root():
    return {"message": "IntellInbox API is online"}