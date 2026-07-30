# Phase 6: Tool-Calling、多轮会话与分层记忆

这个阶段的目标，是把前面已经具备的 context、memory、tools 能力真正串起来，形成一个可以多轮运行的 Agent 闭环。

Phase 6 主要解决的问题：

- 模型不再只是返回文本，而是可以发起原生 `tool call`
- Agent 可以执行工具，并把 observation 回填给模型继续推理
- CLI 不再只是单轮 one-shot，而是支持一个 session 内的多轮对话
- 短期会话历史和长期记忆做明确分层

这个阶段的核心模块包括：

- `agent_lab/agent/loop.py`：单轮内的 tool-calling 循环
- `agent_lab/harness/session.py`：多轮 session 管理
- `agent_lab/harness/cli.py`：交互式命令行入口
- `agent_lab/model/azure_client.py`：模型客户端与结构化 tool call 解析
- `agent_lab/memory/jsonl_store.py`：长期记忆存储
- `agent_lab/tools/`：工具协议与内置工具

在职责边界上：

- `AgentLoop` 负责单轮执行
- `SessionHarness` 负责跨轮短期历史
- `JsonlMemoryStore` 负责长期记忆

也就是说，这一阶段的重点不是“更复杂的模型能力”，而是把 Agent 的执行闭环、工具使用和会话生命周期先搭稳。 
