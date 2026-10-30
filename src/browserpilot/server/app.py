"""FastAPI application factory, lifespan management, and static asset serving."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from browserpilot.server.routes import router, state


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and clean teardown of browser processes."""
    yield
    # Cleanup on shutdown
    if state.relay:
        await state.relay.stop_stream()
    if state.browser_manager:
        await state.browser_manager.close()


def create_app() -> FastAPI:
    """Build and configure the BrowserPilot FastAPI application."""
    app = FastAPI(
        title="BrowserPilot Mission Control API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Mount compiled React 19 frontend if available
    web_dist = Path(__file__).resolve().parent.parent.parent.parent / "web" / "dist"
    if web_dist.exists() and (web_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(web_dist), html=True), name="static")
    else:
        @app.get("/", response_class=HTMLResponse)
        async def root() -> str:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>BrowserPilot Studio</title>
                <style>
                    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
                    .card { background: #1e293b; padding: 2rem 3rem; border-radius: 12px; border: 1px solid #334155; text-align: center; max-width: 500px; }
                    h1 { margin-top: 0; color: #38bdf8; }
                    p { color: #94a3b8; line-height: 1.6; }
                    a { color: #38bdf8; text-decoration: none; font-weight: 500; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>BrowserPilot Backend Running</h1>
                    <p>The mission control API is listening on port 9660. The React 19 web frontend can be served independently or built via <code>npm run build</code> inside the <code>web/</code> directory.</p>
                    <p><a href="/docs">View OpenAPI Swagger Documentation &rarr;</a></p>
                </div>
            </body>
            </html>
            """

    return app
