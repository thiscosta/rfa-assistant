from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cases, clinic, documents, form, meta
from app.core.config import CLAUDE_MODEL, CORS_ORIGINS
from app.core.credentials import require_credentials
from app.pipeline.processing import resume_interrupted

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("rfa")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Claude is the only reader: refuse to start rather than accept documents that can never be read.
    source = require_credentials()
    log.info("Claude credentials: %s, model %s", source, CLAUDE_MODEL)
    resume_interrupted()
    yield


app = FastAPI(title="RFA Assistant", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Page", "Content-Disposition"],
)

for module in (meta, clinic, cases, documents, form):
    app.include_router(module.router)
