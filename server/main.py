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


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return """<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ask Michal - צ'אט</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f0f2f5;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            background: linear-gradient(135deg, #1a3a2a, #2d5a3f);
            color: white;
            padding: 14px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        .header-avatar {
            width: 40px; height: 40px;
            background: rgba(255,255,255,0.2);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .header h1 { font-size: 18px; font-weight: 600; }
        .header-info { margin-right: auto; display: flex; align-items: center; gap: 12px; font-size: 13px; opacity: 0.85; }
        .quota-badge { background: rgba(255,255,255,0.2); padding: 4px 10px; border-radius: 12px; font-size: 12px; }
        .logout-btn { background: none; border: 1px solid rgba(255,255,255,0.3); color: white; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
        .logout-btn:hover { background: rgba(255,255,255,0.1); }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        .message {
            max-width: 75%;
            padding: 14px 18px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 15px;
            white-space: pre-wrap;
        }
        .message.user {
            align-self: flex-start;
            background: #2e7d32;
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.bot {
            align-self: flex-end;
            background: white;
            color: #333;
            border-bottom-left-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .message.bot .sources {
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #888;
        }
        .message.system {
            align-self: center;
            background: #fff3cd;
            color: #856404;
            font-size: 13px;
            max-width: 90%;
            text-align: center;
        }
        .typing {
            align-self: flex-end;
            background: white;
            padding: 14px 18px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: none;
        }
        .typing .dots { display: inline-flex; gap: 4px; }
        .typing .dot {
            width: 8px; height: 8px;
            background: #aaa;
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }
        .typing .dot:nth-child(2) { animation-delay: 0.2s; }
        .typing .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-6px); }
        }
        .input-area {
            padding: 16px 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }
        .input-area input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 15px;
            font-family: inherit;
            outline: none;
            direction: rtl;
        }
        .input-area input:focus { border-color: #2e7d32; }
        .send-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #2e7d32, #43a047);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s;
        }
        .send-btn:hover { transform: scale(1.02); }
        .send-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        @media (max-width: 600px) {
            .message { max-width: 90%; }
            .header-info span { display: none; }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-avatar">M</div>
        <h1>Ask Michal</h1>
        <div class="header-info">
            <span id="userName"></span>
            <span class="quota-badge" id="quota"></span>
            <button class="logout-btn" onclick="logout()">התנתקות</button>
        </div>
    </div>
    <div class="messages" id="messages">
        <div class="message bot">שלום! אני מיכל, קצינת שלישות וירטואלית. איך אוכל לעזור לך?</div>
    </div>
    <div class="typing" id="typing">
        <div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>
    </div>
    <div class="input-area">
        <input type="text" id="input" placeholder="...שאלי את מיכל" autofocus>
        <button class="send-btn" id="sendBtn" onclick="send()">שלח</button>
    </div>

    <script>
        const token = localStorage.getItem('michal_token');
        const userName = localStorage.getItem('michal_user');
        if (!token) window.location.href = '/';

        document.getElementById('userName').textContent = userName || '';

        // Load quota
        fetch('/api/quota', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(r => r.json())
            .then(d => { document.getElementById('quota').textContent = d.queries_remaining + ' שאלות נותרו'; })
            .catch(() => {});

        const input = document.getElementById('input');
        const messagesDiv = document.getElementById('messages');
        const typingDiv = document.getElementById('typing');
        const sendBtn = document.getElementById('sendBtn');

        input.addEventListener('keydown', e => { if (e.key === 'Enter' && !sendBtn.disabled) send(); });

        function addMessage(text, type, sources) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            if (sources && sources.length > 0) {
                const srcDiv = document.createElement('div');
                srcDiv.className = 'sources';
                srcDiv.textContent = 'מקורות: ' + sources.join(' | ');
                div.appendChild(srcDiv);
            }
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        async function send() {
            const q = input.value.trim();
            if (!q) return;

            addMessage(q, 'user');
            input.value = '';
            sendBtn.disabled = true;
            typingDiv.style.display = 'block';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;

            try {
                const res = await fetch('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                    body: JSON.stringify({ question: q })
                });

                if (res.status === 401) { window.location.href = '/'; return; }
                if (res.status === 429) { addMessage('מכסת השאלות שלך נגמרה. פנה/י למנהל המערכת.', 'system'); return; }

                const data = await res.json();
                if (res.ok) {
                    addMessage(data.answer, 'bot', data.sources);
                    document.getElementById('quota').textContent = data.queries_remaining + ' שאלות נותרו';
                } else {
                    addMessage(data.detail || 'שגיאה בלתי צפויה', 'system');
                }
            } catch (err) {
                addMessage('שגיאת תקשורת. נסה/י שנית.', 'system');
            } finally {
                typingDiv.style.display = 'none';
                sendBtn.disabled = false;
                input.focus();
            }
        }

        function logout() {
            localStorage.removeItem('michal_token');
            localStorage.removeItem('michal_user');
            window.location.href = '/';
        }
    </script>
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
