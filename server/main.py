# -*- coding: utf-8 -*-
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from server.config import Settings
from server.database import init_db
from server.auth.oauth import router as auth_router
from server.api.routes import router as api_router
from server.api.admin import router as admin_router
from server.rag.retriever import KnowledgeRetriever
from server.ai.engine import MichalEngine

logger = logging.getLogger("ask-michal")
settings = Settings()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    init_db()

    logger.info("Loading embedding model and knowledge base...")
    retriever = KnowledgeRetriever(settings)

    if not retriever.is_ready():
        logger.warning(
            "Knowledge base is empty! Run 'python -m scripts.ingest_kb' to ingest PDFs."
        )

    app.state.engine = MichalEngine(settings, retriever)
    logger.info("Ask Michal server ready.")
    yield
    # Shutdown


app = FastAPI(
    title="Ask Michal API",
    description="AI HR Assistant for Division 96",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow the domain and localhost for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(admin_router)


def _read_html(filename: str) -> str:
    with open(os.path.join(STATIC_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return _read_html("home.html")


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return _read_html("chat.html")


def run():
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
