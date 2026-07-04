from collections import defaultdict, deque
from contextvars import ContextVar
from uuid import uuid4
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

# -----------------------------
# Configuration
# -----------------------------

# Replace with your logged-in email address
EMAIL = "24f2006126@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://app-9y5os1.example.com"

# Also add the exam page origin used by the grader.
# Replace with the actual exam origin if different.
EXTRA_ALLOWED_ORIGIN = "https://exam.example.com"

RATE_LIMIT = 8
WINDOW_SECONDS = 10

# -----------------------------
# Request Context
# -----------------------------

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())

        request.state.request_id = request_id
        request_id_ctx.set(request_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        return response


# -----------------------------
# Rate Limiter
# -----------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.clients = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")

        now = time.time()
        bucket = self.clients[client_id]

        while bucket and now - bucket[0] >= WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        bucket.append(now)

        return await call_next(request)


# -----------------------------
# FastAPI App
# -----------------------------

app = FastAPI()

# Middleware order:
# Request Context -> CORS -> Rate Limiter (composition requirement)
app.add_middleware(RequestContextMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        EXTRA_ALLOWED_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }