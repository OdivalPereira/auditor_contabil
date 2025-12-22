from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
import time
from src.api.endpoints import upload, reconcile, scan, export, extract
from src.common.logging_config import setup_logging, set_request_id, get_logger

# Initialize Structured Logging
setup_logging()
logger = get_logger("api.main")

app = FastAPI(title="Auditor Contábil API", version="1.0.0")

# Middleware for Request ID and Logging
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    
    start_time = time.time()
    
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra_fields={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else "unknown"
        }
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        logger.info(
            f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",
            extra_fields={
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2)
            }
        )
        
        # Add request ID to response headers for tracking
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {str(e)}",
            extra_fields={
                "error": str(e),
                "process_time_ms": round(process_time * 1000, 2)
            },
            exc_info=True
        )
        raise

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
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(extract.router, prefix="/api/extract", tags=["Extract"])

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "Auditor Contábil"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010)
