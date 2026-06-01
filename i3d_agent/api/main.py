"""FastAPI application for I3D Agent System."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from i3d_agent.api.routes.chat import router as chat_router
from i3d_agent.utils.logger import get_logger
from i3d_agent.utils.telemetry import instrument_fastapi

logger = get_logger(__name__)


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

    return app


app = create_app()
