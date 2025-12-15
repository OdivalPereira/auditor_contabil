from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.endpoints import upload, reconcile, scan

app = FastAPI(title="Auditor Contábil API", version="1.0.0")

# CORS Setup - Enable frontend access
origins = [
    "http://localhost:5173", # Vite Default
    "http://localhost:3000",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(reconcile.router, prefix="/api/reconcile", tags=["Reconcile"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scan"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Auditor Contábil"}
