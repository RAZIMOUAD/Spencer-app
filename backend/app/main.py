"""FastAPI application entry point for Spencer slope stability analysis."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.errors import register_exception_handlers
from app.api.routes import analysis as analysis_router

app = FastAPI(
    title="Spencer — Stabilité des Talus",
    description="API d'analyse de stabilité des pentes par méthode de Spencer (Eurocode 7 / EN 1997-1)",
    version="0.1.0",
)

# ---------------------------------------------------------------------------
# CORS — allow Next.js dev server
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
register_exception_handlers(app)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(analysis_router.router, prefix="/api/analysis", tags=["analysis"])


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": "spencer-backend"}
