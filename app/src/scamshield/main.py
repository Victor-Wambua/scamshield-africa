"""Application factory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, get_settings
from .db import Database
from .web import api, auth, org, public, staff
from .web.deps import TEMPLATES, count_synthetic

MAX_BODY = 30 * 1024 * 1024
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'; object-src 'none'"
DOCS_CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; frame-ancestors 'none'"


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate()
    app = FastAPI(
        title="ScamShield Africa API",
        version="0.1.0",
        description="Fraud-intelligence lookup and reporting API. Pilot MVP: synthetic demonstration data only unless stated. Not proof of fraud: results describe what has been reported.",
        docs_url=None, redoc_url=None, openapi_url="/openapi.json",
    )
    app.state.settings = settings
    app.state.database = database or Database(settings.database_url)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    _demo_cache: dict[str, bool | None] = {"v": None}

    def demo_flag() -> bool:
        if _demo_cache["v"] is None:
            with app.state.database.factory() as db:
                _demo_cache["v"] = bool(count_synthetic(db))
        return bool(_demo_cache["v"])

    app.state.demo_flag = demo_flag
    app.state.reset_demo_flag = lambda: _demo_cache.update(v=None)

    static_dir = Path(__file__).parent / "web" / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(staff.router)
    app.include_router(org.router)
    app.include_router(api.router)

    @app.get("/docs", include_in_schema=False)
    def docs_page() -> Response:
        from fastapi.openapi.docs import get_swagger_ui_html

        r = get_swagger_ui_html(openapi_url="/openapi.json", title="ScamShield Africa API", swagger_js_url="/static/swagger/swagger-ui-bundle.js", swagger_css_url="/static/swagger/swagger-ui.css")
        r.headers["Content-Security-Policy"] = DOCS_CSP
        return r

    @app.middleware("http")
    async def secure(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        cl = request.headers.get("content-length")
        if cl and cl.isdigit() and int(cl) > MAX_BODY:
            return JSONResponse({"error": {"code": "too_large", "message": "Request too large"}}, status_code=413)
        resp = await call_next(request)
        h = resp.headers
        h.setdefault("Content-Security-Policy", CSP)
        h["X-Content-Type-Options"] = "nosniff"
        h["X-Frame-Options"] = "DENY"
        h["Referrer-Policy"] = "same-origin"
        h["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.cookie_secure:
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if not request.url.path.startswith("/static"):
            h.setdefault("Cache-Control", "no-store")
        return resp

    @app.exception_handler(api.ApiError)
    async def _api_error(_: Request, exc: api.ApiError) -> JSONResponse:
        return api.error_response(exc)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": {"code": "invalid_request", "message": "Invalid request.", "details": [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]}}, status_code=422)
        return _html_error(request, 422, "Invalid request", "Something in the request was not valid.")

    def _html_error(request: Request, status: int, title: str, message: str) -> Response:
        from .web.deps import Ctx

        db = request.app.state.database.factory()
        try:
            ctx = Ctx(request, db)
            return ctx.render("error.html", status, title=title, message=message, show_login=status == 401)
        finally:
            db.close()

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": {"code": "http_error", "message": str(exc.detail)}}, status_code=exc.status_code, headers=getattr(exc, "headers", None))
        if exc.status_code in (301, 302, 303, 307, 308) and exc.headers and "Location" in exc.headers:
            return RedirectResponse(exc.headers["Location"], status_code=303)
        if exc.status_code == 401:
            return _html_error(request, 401, "Sign in required", "Please sign in to continue.")
        if exc.status_code == 403 and exc.detail == "csrf":
            return _html_error(request, 403, "Session expired", "Your form expired or could not be verified. Go back, reload the page and try again.")
        if exc.status_code == 403:
            return _html_error(request, 403, "This area is restricted", "Your account does not have access to this page.")
        if exc.status_code == 404:
            return _html_error(request, 404, "Page not found", "That page does not exist or is not available to you.")
        return _html_error(request, exc.status_code, "Something went wrong", "Please try again.")

    @app.exception_handler(Exception)
    async def _crash(request: Request, exc: Exception) -> Response:  # pragma: no cover - last resort
        import logging

        logging.getLogger("scamshield").exception("unhandled error", exc_info=exc)
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": {"code": "server_error", "message": "Internal error"}}, status_code=500)
        return _html_error(request, 500, "Something went wrong", "We hit a problem. Nothing was lost. Please try again.")

    _ = (HTTPException, TEMPLATES)
    return app


def app_factory() -> FastAPI:
    return create_app()
