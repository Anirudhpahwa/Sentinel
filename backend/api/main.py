from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import executions, jobs, workers

app = FastAPI(title="Sentinel API")

# Phase 1 has no auth and no fixed frontend origin yet; tighten this once
# real users/auth are introduced.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(executions.router)
app.include_router(workers.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
