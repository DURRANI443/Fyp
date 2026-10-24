import time
import asyncio
import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.auth import router as auth_router
from app.config import PROJECT_ROOT, settings
from app.db import SessionLocal
from app.routes.core import router as core_router
from app.routes.support import router as support_router
from app.routes.checkout import router as checkout_router
from app.seed import seed_demo


def create_app(seed=True):
    @asynccontextmanager
    async def lifespan(app):
        if settings.app_env == "production":
            from app.manage_users import assert_no_default_demo_passwords
            with SessionLocal() as db:
                assert_no_default_demo_passwords(db)
        if seed and settings.seed_demo:
            with SessionLocal() as db:
                seed_demo(db)
        if seed:
            from app.ai.engine import warmup
            logger = logging.getLogger("uvicorn.error")
            logger.info("Preparing local AI. A cached embedding model can take about a minute on first load.")
            prepared = await asyncio.to_thread(warmup)
            logger.info("Local AI ready: %s", prepared["retrieval"])
        yield

    app = FastAPI(title="Northstar Support API", version="0.3.0", lifespan=lifespan,
                  description="Local FYP demonstration. Synthetic store data; no real payment processing.")
    app.state.rate_buckets = defaultdict(deque)
    app.state.rate_lock = Lock()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.hosts)
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                       allow_headers=["Content-Type", "X-CSRF-Token"])

    @app.middleware("http")
    async def request_guards(request: Request, call_next):
        if request.url.path.startswith("/api"):
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                if origin and origin not in settings.origins:
                    return JSONResponse({"detail": "Request origin is not allowed."}, status_code=403)
                length = request.headers.get("content-length", "0")
                if not length.isdigit() or int(length) > 65536:
                    return JSONResponse({"detail": "Request is too large."}, status_code=413)
                if request.url.path == "/api/auth/login" and "application/json" not in request.headers.get("content-type", ""):
                    return JSONResponse({"detail": "Use JSON for sign-in."}, status_code=415)
                # A bounded demo limiter; production multi-worker limits need shared storage.
                now = time.monotonic()
                tag = "login" if request.url.path.endswith("/auth/login") else "write"
                key = (request.client.host if request.client else "local", tag)
                limit = 30 if tag == "login" else 120
                with app.state.rate_lock:
                    bucket = app.state.rate_buckets[key]
                    while bucket and bucket[0] <= now - 60:
                        bucket.popleft()
                    if len(bucket) >= limit:
                        return JSONResponse({"detail": "Too many requests. Please wait a minute."}, 429, headers={"Retry-After": "60"})
                    bucket.append(now)
            response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    app.include_router(auth_router, prefix="/api")
    app.include_router(core_router, prefix="/api")
    app.include_router(support_router, prefix="/api")
    app.include_router(checkout_router, prefix="/api")
    dist = PROJECT_ROOT / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
