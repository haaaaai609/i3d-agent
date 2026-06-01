"""FastAPI application for I3D Agent System."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from i3d_agent.api.routes.chat import router as chat_router
from i3d_agent.utils.logger import get_logger
from i3d_agent.utils.telemetry import instrument_fastapi

logger = get_logger(__name__)

# Static files directory
STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理。"""
    logger.info("Starting I3D Agent API...")
    yield
    logger.info("Shutting down I3D Agent API...")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例。"""
    app = FastAPI(
        title="I3D Agent System API",
        description="Intelligent multi-agent system for data processing and analysis",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"])

    # 仪器化
    instrument_fastapi(app)

    # 健康检查
    @app.get("/health")
    async def health_check():
        """健康检查端点。"""
        return {"status": "healthy", "service": "i3d-agent-api"}

    # 根路径 - 重定向到聊天界面
    @app.get("/")
    async def root():
        """根路径 - 返回聊天界面。"""
        chat_html = STATIC_DIR / "chat.html"
        if chat_html.exists():
            return FileResponse(chat_html)
        return {"message": "I3D Agent System API", "docs": "/docs", "chat": "/chat"}

    # 聊天界面
    @app.get("/chat")
    async def chat():
        """聊天界面。"""
        chat_html = STATIC_DIR / "chat.html"
        if chat_html.exists():
            return FileResponse(chat_html)
        return {"error": "Chat interface not found"}

    # 静态文件服务
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        logger.info(f"Serving static files from {STATIC_DIR}")

    return app


app = create_app()
