from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.fittings import router as fitting_router
from app.api.v1.garments import router as garment_router
from app.api.v1.generation import router as generation_router
from app.api.v1.recommendations import router as recommendation_router
from app.api.v1.routes import router
from app.core.config import Settings
from app.core.database import create_database
from app.core.errors import AppError
from app.models import Base
from app.services.garment_ai import GarmentAI


def create_app(settings: Settings | None = None) -> FastAPI:
    """인증·비공개 의류 저장·로컬 AI를 개발 환경에서 구성한다."""
    settings = settings or Settings()
    engine, factory = create_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app):
        # 로컬 개발 초기화. 운영 DB에는 Alembic migration을 먼저 적용한다.
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title="StyleFit AI — Local Development", version="0.5.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = factory
    app.state.garment_ai = GarmentAI()
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=[
            "Content-Type",
            "X-Upload-Rights",
            "Authorization",
            "X-Image-Processing-Consent",
            "X-Image-Storage-Consent",
            "X-Evidence-Storage-Consent",
        ],
    )

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        client = request.client.host if request.client else ""
        origin = request.headers.get("origin")
        if client not in {"127.0.0.1", "::1", "testclient"} or (
            origin is not None and origin not in settings.cors_origins
        ):
            return JSONResponse(
                {
                    "error": {
                        "code": "LOCAL_ONLY",
                        "message": "로컬 개발 환경에서만 사용할 수 있습니다.",
                    }
                },
                status_code=403,
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )
        # Pydantic JSON 파싱 전에도 chunked body를 포함해 총 요청 크기를 제한한다.
        received = 0
        chunks = []
        async for chunk in request.stream():
            received += len(chunk)
            if received > settings.max_request_bytes:
                return JSONResponse(
                    {"error": {"code": "REQUEST_TOO_LARGE", "message": "사진 묶음이 너무 큽니다."}},
                    status_code=413,
                    headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
                )
            chunks.append(chunk)
        # Starlette의 downstream 요청은 이미 검증한 캐시를 읽는다.
        request._body = b"".join(chunks)
        chunks.clear()
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, error: AppError):
        return JSONResponse(
            {"error": {"code": error.code, "message": error.message}}, status_code=error.status
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(_request: Request, error: HTTPException):
        return JSONResponse(
            {"error": {"code": "REQUEST_REJECTED", "message": str(error.detail)}},
            status_code=error.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, _error: RequestValidationError):
        return JSONResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": "입력 내용을 확인해 주세요."}},
            status_code=400,
        )

    app.include_router(router, prefix="/api/v1")
    app.include_router(garment_router, prefix="/api/v1")
    app.include_router(generation_router, prefix="/api/v1")
    app.include_router(fitting_router, prefix="/api/v1")
    app.include_router(recommendation_router, prefix="/api/v1")
    return app


app = create_app()
