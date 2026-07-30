# agent-from0to1

这是一个按阶段独立演进的 Python Agent 实验项目。

项目目标是从最小可运行的 `agent loop` 出发，逐步补齐一个 Agent 系统常见的核心能力，包括：

- `context`：上下文组织与注入
- `memory`：长期记忆读写与召回
- `tools`：工具协议、注册和调用
- `tool-calling`：模型原生工具调用循环
- `reflection / evaluator`：后续阶段继续补充
- `multi-agent`：后续阶段继续扩展

仓库采用“每个阶段一个独立目录”的方式组织，方便对比每一步设计演进，而不是在同一份代码上持续覆盖。

当前主要阶段：

- `phases/phase3_context`
- `phases/phase4_memory`
- `phases/phase5_tools`
- `phases/phase6_tool_calling`

当前最新阶段是 `phases/phase6_tool_calling`。
