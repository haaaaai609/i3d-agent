"""RAG API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from i3d_agent.rag.models import (
    DocumentCreate, DocumentUpdate, DocumentResponse,
    SearchRequest, AskRequest, FeedbackRequest
)
from i3d_agent.rag.document_manager import DocumentManager
from i3d_agent.rag.controller import AgenticRAGController
from i3d_agent.rag.monitor import MonitorService
from i3d_agent.rag.index_worker import IndexWorker
from i3d_agent.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


# ========== 依赖注入 ==========

async def get_document_manager() -> DocumentManager:
    """获取文档管理器实例"""
    return DocumentManager()


async def get_rag_controller() -> AgenticRAGController:
    """获取 RAG 控制器实例"""
    return AgenticRAGController()


async def get_monitor_service() -> MonitorService:
    """获取监控服务实例"""
    return MonitorService()


# ========== 文档管理 API ==========

@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    request: DocumentCreate,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """创建新文档"""
    try:
        doc = await document_manager.create_document(
            tenant_id=request.tenant_id,
            title=request.title,
            content=request.content,
            doc_type=request.doc_type,
            source_type=request.source_type,
            description=request.description,
            metadata=request.metadata,
            tags=request.tags,
            language=request.language
        )
        return doc
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """获取文档详情"""
    doc = await document_manager.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    request: DocumentUpdate,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """更新文档"""
    try:
        doc = await document_manager.update_document(
            doc_id=doc_id,
            content=request.content,
            title=request.title,
            description=request.description,
            metadata=request.metadata,
            tags=request.tags
        )
        return doc
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    hard_delete: bool = False,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """删除文档"""
    try:
        await document_manager.delete_document(doc_id, hard_delete=hard_delete)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{doc_id}/restore", response_model=DocumentResponse)
async def restore_document(
    doc_id: str,
    version: Optional[int] = None,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """恢复文档"""
    try:
        doc = await document_manager.restore_document(doc_id, version)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to restore document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}/history")
async def get_document_history(
    doc_id: str,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """获取文档版本历史"""
    try:
        history = await document_manager.get_document_history(doc_id)
        return {"history": history}
    except Exception as e:
        logger.error(f"Failed to get document history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(
    tenant_id: str,
    doc_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    document_manager: DocumentManager = Depends(get_document_manager)
):
    """列出文档（分页）"""
    try:
        result = await document_manager.list_documents(
            tenant_id=tenant_id,
            doc_type=doc_type,
            page=page,
            page_size=page_size
        )
        return result
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 检索与问答 API ==========

@router.post("/search")
async def search(
    request: SearchRequest,
    rag_controller: AgenticRAGController = Depends(get_rag_controller)
):
    """检索接口（返回文档片段）"""
    try:
        from i3d_agent.rag.embedding import EmbeddingService
        embedding_service = EmbeddingService()

        # 生成查询向量
        query_vector = await embedding_service.embed_text(request.query)

        # 执行检索
        result = await rag_controller.retrieve(
            query=request.query,
            tenant_id=request.tenant_id,
            top_k=request.top_k,
            enable_expansion=request.enable_expansion,
            enable_hyde=request.enable_hyde,
            enable_rerank=request.enable_rerank,
            search_type=request.search_type
        )

        return {
            "query": result.query,
            "results": [
                {
                    "chunk_id": r.id,
                    "doc_id": r.doc_id,
                    "content": r.content,
                    "score": r.final_score,
                    "metadata": r.metadata
                }
                for r in result.results
            ],
            "total": len(result.results),
            "iterations": result.iterations,
            "query_expansions": result.query_expansions
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ask")
async def ask(
    request: AskRequest,
    rag_controller: AgenticRAGController = Depends(get_rag_controller)
):
    """RAG 问答（返回完整答案）"""
    try:
        from i3d_agent.rag.embedding import EmbeddingService
        embedding_service = EmbeddingService()

        # 生成查询向量
        query_vector = await embedding_service.embed_text(request.question)

        # 执行检索
        result = await rag_controller.retrieve(
            query=request.question,
            tenant_id=request.tenant_id,
            top_k=request.top_k,
            enable_expansion=True,
            enable_hyde=True,
            enable_rerank=True,
            enable_multi_step=request.enable_multi_step
        )

        if not result.results:
            return {
                "question": request.question,
                "answer": "抱歉，知识库中没有找到相关文档。",
                "sources": [],
                "status": "no_results"
            }

        # 构建上下文
        context_parts = []
        for i, r in enumerate(result.results, 1):
            title = r.metadata.get("title", "Unknown")
            content = r.content
            score = r.final_score or 0
            context_parts.append(f"[文档 {i}] {title} (相关度: {score:.2f})\n{content}")

        context = "\n\n".join(context_parts)

        # 生成答案
        from i3d_agent.llm import get_llm_client, Message

        system_prompt = """你是一个技术文档助手，专门回答关于 3D CAD 系统、搜索服务、部署和故障排查的问题。

请根据提供的文档上下文回答用户问题。如果文档中没有相关信息，请诚实地说明。

回答要求：
1. 准确、简洁、专业
2. 引用相关的文档来源
3. 如果需要步骤，请按顺序列出
4. 使用中文回答"""

        user_prompt = f"""问题: {request.question}

相关文档:
{context}

请根据上述文档回答问题。"""

        llm_client = get_llm_client()
        answer = await llm_client.generate(
            messages=[Message(role="user", content=user_prompt)],
            system_prompt=system_prompt,
            temperature=0.7
        )

        return {
            "question": request.question,
            "answer": answer,
            "sources": [
                {
                    "doc_id": r.doc_id,
                    "title": r.metadata.get("title", "Unknown"),
                    "score": r.final_score
                }
                for r in result.results[:3]
            ],
            "status": "success",
            "metadata": {
                "iterations": result.iterations,
                "num_retrieved": len(result.results)
            }
        }

    except Exception as e:
        logger.error(f"Ask failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 监控 API ==========

@router.get("/index/status")
async def get_index_status(
    tenant_id: str,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取索引状态"""
    try:
        stats = await monitor.get_index_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get index status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/queue")
async def get_index_queue(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 50
):
    """获取索引队列"""
    try:
        from i3d_agent.config.settings import get_settings
        settings = get_settings()
        pool = await (await DocumentManager()._get_pool()).acquire()

        conditions = ["tenant_id = $1"]
        params = [tenant_id]
        param_count = 1

        if status:
            param_count += 1
            conditions.append(f"status = ${param_count}")
            params.append(status)

        query = f"""
            SELECT id, doc_id, operation, status, priority,
                   retry_count, error_message, created_at, started_at
            FROM rag_index_queue
            WHERE {' AND '.join(conditions)}
            ORDER BY priority DESC, created_at ASC
            LIMIT ${param_count + 1}
        """
        params.append(limit)

        rows = await pool.fetch(query, *params)
        return {"tasks": [dict(row) for row in rows]}

    except Exception as e:
        logger.error(f"Failed to get index queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(
    tenant_id: str,
    metric_name: Optional[str] = None,
    time_range: str = "24h",
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取监控指标"""
    try:
        metrics = await monitor.get_metrics(tenant_id, metric_name, time_range)
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_quality_metrics(
    tenant_id: str,
    days: int = 7,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """获取质量指标"""
    try:
        metrics = await monitor.get_quality_metrics(tenant_id, days)
        return metrics
    except Exception as e:
        logger.error(f"Failed to get quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    monitor: MonitorService = Depends(get_monitor_service)
):
    """提交质量反馈"""
    try:
        await monitor.save_feedback(
            tenant_id="default",  # TODO: 从请求中获取
            session_id=request.session_id,
            query=request.query,
            retrieved_doc_ids=request.retrieved_doc_ids,
            rating=request.rating,
            is_helpful=request.is_helpful,
            thumb_up=request.thumb_up,
            feedback_text=request.feedback_text,
            answer=None,
            sources=None
        )
        return {"message": "Feedback recorded successfully"}
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))
