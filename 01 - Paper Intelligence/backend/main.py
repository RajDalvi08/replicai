from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from backend.code import (
    models as code_models,  # noqa: F401  # ensure code models registered
)
from backend.code.router import router as code_router  # type: ignore[attr-defined]
from backend.database import Base, engine
from backend.paper import models  # noqa: F401  # ensure model metadata is registered
from backend.paper.exceptions import PaperProcessingError
from backend.paper.router import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ReplicAI Paper Intelligence")
app.include_router(router, prefix="/api/v1")
app.include_router(code_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": detail["error"], "message": detail.get("message", "")},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": str(detail)},
    )


@app.exception_handler(PaperProcessingError)
async def paper_processing_error_handler(_, exc: PaperProcessingError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.code, "message": str(exc)})
