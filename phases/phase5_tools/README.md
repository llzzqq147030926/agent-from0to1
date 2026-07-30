# Phase 5: Tool 系统

本目录是 Phase 5 的独立代码快照，基于 `phases/phase4_memory` 演进。根目录和 Phase 4 目录不被覆盖，便于阶段间对比。

## 目标

- 实现 tool protocol。
- 实现 tool registry。
- 实现严格参数校验。
- 增加第一批工具：
  - `write_file`：写入或追加本地 UTF-8 文本文件。
  - `read_file`：读取本地 UTF-8 文本文件。
  - `bash`：在 workspace 内执行本地 shell 命令。
  - `fetch_url`：访问 HTTP/HTTPS URL。
  - `memory_append`：显式写入长期 memory。

## 实现内容

- `agent_lab/tools/base.py`
  - `ToolSchema`：工具名称、描述和参数 schema。
  - `ToolRegistry`：注册工具、执行工具、导出 OpenAI function tool schema。
  - `ToolParameterError`：工具参数不符合 schema 时严格报错。
- `agent_lab/tools/file.py`
  - `LocalFileWriteTool`：限制写入路径必须位于 workspace root 内。
  - 支持 `overwrite` 与 `append` 两种模式。
  - 默认创建缺失的父目录。
  - `LocalFileReadTool`：限制读取路径必须位于 workspace root 内。
- `agent_lab/tools/shell.py`
  - `BashTool`：在 workspace root 内执行 `bash -lc` 命令。
  - 支持指定相对 `cwd` 和正整数超时。
- `agent_lab/tools/web.py`
  - `FetchUrlTool`：使用标准库获取 HTTP/HTTPS 文本响应。
  - 支持正整数超时，返回状态码、content type、文本和字节数。
- `agent_lab/tools/memory.py`
  - `MemoryAppendTool`：通过工具显式写入 JSONL memory。
- `agent_lab/memory/jsonl_store.py`
  - `MemoryRecord`：单条 memory 记录。
  - `JsonlMemoryStore.append()`：追加写入 JSONL。
  - `JsonlMemoryStore.recall()`：按关键词交集召回。
  - `JsonlMemoryStore.load_all()`：读取历史 memory。
- `agent_lab/agent/loop.py`
  - 每轮开始前按 `user_goal` 召回 memory。
  - 将召回结果注入为一个 `## memory` context section。
  - 不再在模型成功返回后自动写入长期 memory。
- `agent_lab/harness/cli.py`
  - 默认使用 `memory/agent_memory.jsonl`。
  - 支持通过 `--memory-file` 指定 memory 文件。
  - 支持通过 `--memory-recall-limit` 控制单轮召回数量。

## 边界

- Phase 5 只实现工具系统本身，不实现模型自动 tool-calling loop。
- `ToolRegistry.openai_tools()` 已能导出原生 function tool schema，供后续 Phase 6 传入模型 API。
- `tool_sections` 仍只适合放工具使用策略和约束，不用于重复注入完整 JSON schema。
- Memory 写入必须由 `memory_append` 显式触发；AgentLoop 不自动把每轮回答写入长期记忆。
- Memory 模块不负责压缩、总结、重要性评分或 embedding recall。
- Context 模块只接收 memory section，不负责 memory 读写。
- 当前 recall 是粗糙关键词交集检索，只用于验证 memory 读写链路；后续阶段需要重构为更可靠的检索策略，例如更好的分词、BM25、embedding recall 或 vector store。

## 验证

在本目录执行：

```bash
python3 -m compileall agent_lab tests
python3 -m unittest discover -s tests
```

当前结果：20 个测试全部通过。
