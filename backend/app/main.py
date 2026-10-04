"""ROCKET FORENSICS - TEAM ROCKET. FastAPI application factory."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import get_db, init_indexes
from app.routers import acquisition, analysis, auth, cases, custody, devices, evidence, forensic_images, health, reports, search, timeline
from app.utils.errors import AppError

log = logging.getLogger("rocket")


def _err(status: int, code: str, message: str, details=None) -> JSONResponse:
    body = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content={"success": False, "error": body})


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.jwt_secret in ("", "CHANGE_ME") or len(settings.jwt_secret) < 16:
        if settings.is_production:
            raise RuntimeError("JWT_SECRET must be set to a strong random value (>=16 chars) in production.")
        logging.getLogger("rocket").warning("JWT_SECRET is weak/default - fine for local dev only.")
    logging.basicConfig(level=settings.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            init_indexes(get_db())
        except Exception as e:  # keep API up so /health can report the DB problem
            log.error("Could not create MongoDB indexes: %s", e)
        yield

    app = FastAPI(
        lifespan=lifespan,
        title="ROCKET FORENSICS API",
        description="TEAM ROCKET - Multi-Vendor DVR/NVR Forensic Analysis Platform. Standard exported/CCTV container analysis, read-only forensic image ingestion, standard signature carving, object/motion/face detection, integrity verification, timeline, correlation, custody, and reporting are implemented. OEM proprietary filesystem parsing and OEM deleted-record reconstruction remain extension modules.",
        version=settings.app_version)

    for d in (settings.evidence_dir, settings.processed_dir, settings.snapshots_dir, settings.reports_dir, settings.forensic_images_dir):
        d.mkdir(parents=True, exist_ok=True)

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"], expose_headers=["Content-Range", "Accept-Ranges"])

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _err(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [{"loc": [str(x) for x in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return _err(422, "VALIDATION_ERROR", "Request validation failed.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {400: "BAD_REQUEST", 401: "NOT_AUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND",
                405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return _err(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("Unhandled error")
        msg = "Internal server error." if settings.is_production else f"{type(exc).__name__}: {exc}"
        return _err(500, "INTERNAL_ERROR", msg)

    for r in (health, auth, cases, search, evidence, devices, analysis, timeline, custody, reports, forensic_images, acquisition):
        app.include_router(r.router)
    return app


app = create_app()
