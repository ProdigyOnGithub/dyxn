from fastapi import FastAPI
from db.postgres import engine
from db.models import Base
from api.routes import chat, documents

# keep the tables around even though we're not logging people in yet
Base.metadata.create_all(bind=engine)

app = FastAPI(title="dyxn")

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])


@app.get("/")
def root():
    return {"message": "dyxn api"}
