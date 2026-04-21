"""FastAPI entrypoint + Mangum Lambda handler."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from . import logging as log
from .routers import bots, dashboard, events, secrets

log.configure_logging()

app = FastAPI(title="MCP Platform API", version="0.1.0")

# CORS — Amplify hosted URL + localhost. Tightened via env in prod.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    trace_id = log.new_trace_id()
    log.log(20, "request.in", method=request.method, path=request.url.path)
    try:
        response = await call_next(request)
    except Exception as e:
        log.log(40, "request.error", path=request.url.path, error=str(e))
        raise
    response.headers["x-trace-id"] = trace_id
    log.log(20, "request.out", path=request.url.path, status=response.status_code)
    return response


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": str(exc)})


app.include_router(bots.router)
app.include_router(secrets.router)
app.include_router(events.router)
app.include_router(dashboard.router)


handler = Mangum(app, lifespan="off")
