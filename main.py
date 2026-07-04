from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from uuid import uuid4
import time
from collections import defaultdict, deque

EMAIL = "your-email@example.com"

ALLOWED_ORIGIN = "https://app-9y5os1.example.com"

RATE_LIMIT = 8
WINDOW = 10  # seconds


# -----------------------------
# Request Context Middleware
# -----------------------------
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


# -----------------------------
# Rate Limiter Middleware
# -----------------------------
class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.clients = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")

        now = time.time()
        q = self.clients[client_id]

        while q and now - q[0] > WINDOW:
            q.popleft()

        if len(q) >= RATE_LIMIT:
            return {"detail": "Rate limit exceeded"}

        q.append(now)

        return await call_next(request)


# -----------------------------
# App
# -----------------------------
app = FastAPI()


# IMPORTANT: Request ID FIRST
app.add_middleware(RequestContextMiddleware)


# CORS (must NOT use "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiter last
app.add_middleware(RateLimiterMiddleware)


# -----------------------------
# Endpoint
# -----------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }