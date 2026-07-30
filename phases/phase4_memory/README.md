# Phase 4: Memory 模块

本目录是 Phase 4 的独立代码快照。根目录仍保留 Phase 3 状态，后续阶段继续放在 `phases/<phase_name>/` 下，便于阶段间对比。

## 目标

- 实现本地 JSONL memory。
- 支持 append。
- 支持简单关键词 recall。
- 保存 agent 自我反思结果。

## 实现内容

- `agent_lab/memory/jsonl_store.py`
  - `MemoryRecord`：单条 memory 记录。
  - `JsonlMemoryStore.append()`：追加写入 JSONL。
  - `JsonlMemoryStore.recall()`：按关键词交集召回。
  - `JsonlMemoryStore.load_all()`：读取历史 memory。
- `agent_lab/agent/loop.py`
  - 每轮开始前按 `user_goal` 召回 memory。
  - 将召回结果注入为一个 `## memory` context section。
  - 模型成功返回后，将本次模型回复作为临时 `reflection` 写回 memory。
- `agent_lab/harness/cli.py`
  - 默认使用 `memory/agent_memory.jsonl`。
  - 支持通过 `--memory-file` 指定 memory 文件。
  - 支持通过 `--memory-recall-limit` 控制单轮召回数量。

## 边界

- Memory 模块不负责压缩、总结、重要性评分或 embedding recall。
- Context 模块只接收 memory section，不负责 memory 读写。
- Tool schema 后续应走模型 API 的原生 tools 参数，不在 memory 或 context 中重复维护。
- 当前 `AgentLoop` 成功运行后自动写入 reflection memory，是 Phase 4 的临时闭环实现；成功路径下 `reflection` 暂时等于模型回复内容。后续阶段应改为由显式 memory tool 发起写入，避免每条对话都进入长期记忆。
- 当前 recall 是粗糙关键词交集检索，只用于验证 memory 读写链路；后续阶段需要重构为更可靠的检索策略，例如更好的分词、BM25、embedding recall 或 vector store。

## 验证

在本目录执行：

```bash
python3 -m compileall agent_lab tests
python3 -m unittest discover -s tests
```

当前结果：11 个测试全部通过。
