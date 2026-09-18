from api.routes import auth
from fastapi import FastAPI
from db.postgres import engine
from db.models import Base
from api.routes import chat, documents

from contextlib import asynccontextmanager
import asyncio
from api.services.pubsub_listener import listen_progress

# keep the tables around even though we're not logging people in yet
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(listen_progress())
    yield

app = FastAPI(title="dyxn", lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])


@app.get("/")
def root():
    return {"message": "dyxn api"}
