# -*- coding: utf-8 -*-
import logging
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


@app.get("/", response_class=HTMLResponse)
async def homepage():
    return """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ask Michal - עוזרת שלישות חכמה</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #1a3a2a 0%, #2d5a3f 50%, #1a3a2a 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 50px 40px;
            max-width: 480px;
            width: 90%;
            text-align: center;
        }
        .avatar {
            width: 80px; height: 80px;
            background: linear-gradient(135deg, #2e7d32, #66bb6a);
            border-radius: 50%;
            margin: 0 auto 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            color: white;
        }
        h1 { font-size: 28px; color: #1a3a2a; margin-bottom: 8px; }
        .subtitle { color: #666; font-size: 16px; margin-bottom: 32px; }
        .desc {
            background: #f5f9f6;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 28px;
            font-size: 15px;
            line-height: 1.7;
            color: #444;
            text-align: right;
        }
        .login-btn {
            display: inline-block;
            background: linear-gradient(135deg, #2e7d32, #43a047);
            color: white;
            text-decoration: none;
            padding: 14px 36px;
            border-radius: 8px;
            font-size: 17px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .login-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(46,125,50,0.4);
        }
        .footer {
            margin-top: 28px;
            font-size: 12px;
            color: #999;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="avatar">M</div>
        <h1>Ask Michal</h1>
        <p class="subtitle">עוזרת שלישות חכמה מבוססת בינה מלאכותית</p>
        <div class="desc">
            שלום! אני מיכל, קצינת שלישות וירטואלית.
            אני כאן כדי לעזור לך עם שאלות בנושאי כוח אדם, זכויות, חובות ונהלי שלישות.
        </div>
        <a href="/auth/login" class="login-btn">התחברות עם Google</a>
        <p class="footer">Ask Michal v0.1.0</p>
    </div>
</body>
</html>"""


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
