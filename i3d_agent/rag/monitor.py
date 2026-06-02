"""Monitoring service for RAG performance and quality metrics."""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncpg
from i3d_agent.utils.logger import get_logger
from i3d_agent.config.settings import get_settings

logger = get_logger(__name__)


class MonitorService:
    """监控服务 - 记录和查询 RAG 性能指标"""

    def __init__(self):
        self.settings = get_settings()
        self._pool = None

        # OpenTelemetry 指标
        self._setup_metrics()

    def _setup_metrics(self):
        """设置 OpenTelemetry 指标"""
        try:
            from opentelemetry import metrics
            meter = metrics.get_meter(__name__)

            self.rag_latency = meter.create_histogram(
                "rag检索延迟",
                description="RAG 检索请求处理时间",
                unit="ms"
            )

            self.rag_requests = meter.create_counter(
                "rag检索请求数",
                description="RAG 检索总请求数"
            )

            self.rag_empty_results = meter.create_counter(
                "rag空结果数",
                description="返回空结果的检索数"
            )

        except Exception as e:
            logger.warning(f"Failed to setup OpenTelemetry metrics: {e}")

    async def _get_pool(self) -> asyncpg.Pool:
        """获取数据库连接池"""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.settings.get_database_url(async_driver=True))
        return self._pool

    async def get_index_stats(self) -> Dict[str, Any]:
        """获取索引状态统计"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 总文档数
            total_documents = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_documents
                WHERE is_latest = true AND deleted_at IS NULL
            """)

            # 总 chunk 数
            total_chunks = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_chunks
                WHERE deleted_at IS NULL
            """)

            # 待处理索引
            pending_index = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_index_queue
                WHERE status = 'pending'
            """)

            # 失败索引
            failed_index = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_index_queue
                WHERE status = 'failed'
            """)

            # 正在索引中
            indexing_docs = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_documents
                WHERE status = 'indexing'
            """)

            # 平均 chunk 大小
            avg_chunk_size = await conn.fetchval("""
                SELECT AVG(token_count) FROM rag_chunks
                WHERE deleted_at IS NULL
            """)

            # 文档类型分布
            type_distribution = await conn.fetch("""
                SELECT doc_type, COUNT(*) as count
                FROM rag_documents
                WHERE is_latest = true AND deleted_at IS NULL
                GROUP BY doc_type
            """)

            return {
                "total_documents": total_documents or 0,
                "total_chunks": total_chunks or 0,
                "pending_index": pending_index or 0,
                "failed_index": failed_index or 0,
                "indexing_docs": indexing_docs or 0,
                "avg_chunk_size": int(avg_chunk_size) if avg_chunk_size else 0,
                "doc_type_distribution": {row['doc_type']: row['count'] for row in type_distribution}
            }

    async def record_metric(
        self,
        tenant_id: str,
        metric_name: str,
        value: Dict[str, Any],
        tags: Optional[Dict[str, Any]] = None
    ):
        """记录指标到数据库"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_metrics (tenant_id, metric_name, metric_value, tags)
                VALUES ($1, $2, $3, $4)
            """, tenant_id, metric_name, value, tags or {})

    async def record_latency(self, tenant_id: str, latency_ms: float):
        """记录检索延迟"""
        if hasattr(self, 'rag_latency'):
            self.rag_latency.record(latency_ms, {"tenant_id": tenant_id})

    async def record_request(self, tenant_id: str, has_results: bool):
        """记录检索请求"""
        if hasattr(self, 'rag_requests'):
            self.rag_requests.add(1, {"tenant_id": tenant_id})

        if not has_results and hasattr(self, 'rag_empty_results'):
            self.rag_empty_results.add(1, {"tenant_id": tenant_id})

    async def get_metrics(
        self,
        tenant_id: str,
        metric_name: Optional[str] = None,
        time_range: str = "24h"
    ) -> list:
        """获取监控指标"""
        pool = await self._get_pool()

        # 解析时间范围
        time_delta = self._parse_time_range(time_range)
        since = datetime.now() - time_delta

        async with pool.acquire() as conn:
            conditions = ["timestamp >= $1"]
            params = [since]
            param_count = 1

            if tenant_id:
                param_count += 1
                conditions.append(f"tenant_id = ${param_count}")
                params.append(tenant_id)

            if metric_name:
                param_count += 1
                conditions.append(f"metric_name = ${param_count}")
                params.append(metric_name)

            query = f"""
                SELECT * FROM rag_metrics
                WHERE {' AND '.join(conditions)}
                ORDER BY timestamp DESC
                LIMIT 1000
            """

            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

    def _parse_time_range(self, time_range: str) -> timedelta:
        """解析时间范围"""
        units = {
            'h': 'hours',
            'd': 'days',
            'w': 'weeks'
        }

        for suffix, unit in units.items():
            if time_range.endswith(suffix):
                try:
                    value = int(time_range[:-1])
                    kwargs = {unit: value}
                    return timedelta(**kwargs)
                except ValueError:
                    pass

        return timedelta(hours=24)  # 默认 24 小时

    async def get_quality_metrics(self, tenant_id: str, days: int = 7) -> Dict[str, Any]:
        """获取质量指标"""
        pool = await self._get_pool()

        since = datetime.now() - timedelta(days=days)

        async with pool.acquire() as conn:
            # 平均评分
            avg_rating = await conn.fetchval("""
                SELECT AVG(rating) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND rating IS NOT NULL
            """, tenant_id, since)

            # 有用率
            helpful_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND is_helpful = true
            """, tenant_id, since)

            total_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2
            """, tenant_id, since)

            helpful_rate = helpful_count / total_count if total_count > 0 else 0

            # 点赞率
            thumb_up_count = await conn.fetchval("""
                SELECT COUNT(*) FROM rag_feedback
                WHERE tenant_id = $1 AND created_at >= $2 AND thumb_up = true
            """, tenant_id, since)

            thumb_up_rate = thumb_up_count / total_count if total_count > 0 else 0

            return {
                "avg_rating": float(avg_rating) if avg_rating else None,
                "helpful_rate": helpful_rate,
                "thumb_up_rate": thumb_up_rate,
                "total_feedbacks": total_count
            }

    async def save_feedback(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        retrieved_doc_ids: Optional[list],
        rating: Optional[int],
        is_helpful: Optional[bool],
        thumb_up: Optional[bool],
        feedback_text: Optional[str],
        answer: Optional[str],
        sources: Optional[dict]
    ):
        """保存质量反馈"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO rag_feedback (
                    tenant_id, session_id, query, retrieved_doc_ids,
                    rating, is_helpful, thumb_up, feedback_text, answer, sources
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """, tenant_id, session_id, query, retrieved_doc_ids,
                 rating, is_helpful, thumb_up, feedback_text, answer, sources)

    async def close(self):
        """关闭连接"""
        if self._pool:
            await self._pool.close()
            self._pool = None
