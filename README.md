# I3D Agent System

智能多代理系统，用于数据处理和分析。

## 功能特性

- **多代理协作**: Supervisor、Search、RAG、Process 等 Agent 协同工作
- **LangGraph 工作流**: 基于状态机的工作流编排
- **记忆系统**: 支持工作记忆、用户偏好、搜索历史、语义记忆
- **智能路由**: 自动识别用户意图并路由到合适的 Agent
- **错误恢复**: 支持重试、降级等错误处理策略

## 快速开始

### 本地开发

```bash
# 安装依赖
pip install -r i3d_agent/requirements.txt

# 运行 API
uvicorn i3d_agent.api.main:app --reload --port 8000
```

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 访问 API
curl http://localhost:8000/health
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/v1/chat` | POST | 聊天接口 |

## 项目结构

```
i3d_agent/
├── agents/          # Agent 实现
├── api/             # FastAPI 接口
├── tools/           # 工具定义
├── workflow/        # LangGraph 工作流
├── memory/          # 记忆系统
├── config/          # 配置
├── models/          # 数据模型
└── utils/           # 工具函数
```

## 开发进度

详见 [IMPLEMENTATION_PROGRESS.md](IMPLEMENTATION_PROGRESS.md)

## License

MIT
