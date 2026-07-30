# Progress Log

## 2026-07-27

### 当前阶段

Phase 0：文档与边界定义。

### 已完成

- 创建 `plan.md`。
- 创建 `progress.md`。
- 明确项目目标：
  - 从最小 agent loop 开始。
  - 逐步加入 context、memory、tool、self-optimization、training data export、多 agent。
  - 先通过 trace、evaluator、reflection 建立自我优化闭环，再考虑真实训练或微调。
- 明确当前边界：
  - 本阶段只写文档。
  - 不创建代码文件。
  - 不安装依赖。
  - 不调用模型。

### 已记录的关键决策

- 模型 API key 不写入源码。
- 模型 endpoint、api version、deployment 通过环境变量配置。
- 办公网络 endpoint 使用：

```text
https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl
```

- 非办公网络或原始配置 endpoint 可使用：

```text
https://aidp-i18ntt-sg.byteintl.net/api/modelhub/online/v2/crawl
```

- 后续实现时采用严格契约：
  - 参数缺失直接报错。
  - tool 输入输出不合法直接报错。
  - 模型输出不符合预期直接记录失败。
  - 不做静默降级。

### 待实现

- Phase 1：最小 Agent Loop。
- Phase 2：Trace 与 Progress 记录。
- Phase 3：Context 模块。
- Phase 4：Memory 模块。
- Phase 5：Tool 系统。
- Phase 6：Tool-Calling Agent Loop。
- Phase 7：Evaluator 与 Reflection。
- Phase 8：Self-Optimization 数据闭环。
- Phase 9：多 Agent。

### 下一个建议动作

等待用户明确下一步，例如：

```text
开始实现 Phase 1
```

或：

```text
先细化 Phase 1 的文件结构和接口，不写代码
```

### 作业记录规范

后续每次实现前：

1. 更新当前阶段。
2. 写明本次要做什么。
3. 写明不会做什么。

后续每次实现后：

1. 更新已完成内容。
2. 记录新增文件。
3. 记录验证命令和结果。
4. 记录遗留问题。
5. 记录下一步建议。

---

## 2026-07-27 Phase 1 开工记录

### 当前阶段

Phase 1：最小 Agent Loop。

### 本次要做

- 创建最小 Python 包结构 `agent_lab/`。
- 实现 CLI 入口：

```bash
python -m agent_lab.harness.cli "解释一下你当前能做什么"
```

- 实现最小 agent loop：
  - 接收用户目标。
  - 拼装 system prompt 和 user message。
  - 调用 Azure OpenAI 兼容模型。
  - 输出 assistant answer。
  - 写入一条本地 JSONL 运行记录。

### 本次不会做

- 不实现自动 tool call。
- 不实现长期 memory recall。
- 不实现多 agent。
- 不实现训练任务。
- 不把 API key 写入源码。

### 本次已完成

- 创建最小 Python 包结构 `agent_lab/`。
- 实现 message 契约：
  - `agent_lab/agent/messages.py`
- 实现 run state 与 trace 序列化：
  - `agent_lab/agent/state.py`
- 实现最小 one-shot agent loop：
  - `agent_lab/agent/loop.py`
- 实现模型客户端协议：
  - `agent_lab/model/protocol.py`
- 实现 Azure OpenAI 兼容客户端：
  - `agent_lab/model/azure_client.py`
- 实现 CLI harness：
  - `agent_lab/harness/cli.py`
- 增加运行依赖声明：
  - `requirements.txt`

### 新增文件

- `agent_lab/__init__.py`
- `agent_lab/agent/__init__.py`
- `agent_lab/agent/messages.py`
- `agent_lab/agent/state.py`
- `agent_lab/agent/loop.py`
- `agent_lab/model/__init__.py`
- `agent_lab/model/protocol.py`
- `agent_lab/model/azure_client.py`
- `agent_lab/harness/__init__.py`
- `agent_lab/harness/cli.py`
- `requirements.txt`

### 验证命令和结果

当前环境没有 `python` 命令，因此使用 `python3` 完成验证。

```bash
python3 -m compileall agent_lab
```

结果：通过，所有 Python 文件可编译。

```bash
python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_lab.agent.loop import AgentLoop

class FakeModel:
    def complete(self, messages):
        assert messages[0].role == 'system'
        assert messages[1].role == 'user'
        return '这是一个测试回答。'

with TemporaryDirectory() as tmp:
    trace_file = Path(tmp) / 'agent_runs.jsonl'
    result = AgentLoop(FakeModel(), trace_file=trace_file).run('解释一下你当前能做什么')
    assert result.assistant_answer == '这是一个测试回答。'
    content = trace_file.read_text(encoding='utf-8')
    assert '解释一下你当前能做什么' in content
    assert '这是一个测试回答。' in content
    print('fake loop ok')
PY
```

结果：通过，最小 loop 能返回答案并写入 JSONL trace。

```bash
python3 -m agent_lab.harness.cli --help
```

结果：通过，CLI 可正常展示参数说明。

### 未执行的验证

- 未执行真实模型调用，因为当前会话没有确认 `AZURE_OPENAI_API_KEY` 等环境变量，也不在源码中写入密钥。

真实调用命令：

```bash
python3 -m agent_lab.harness.cli "解释一下你当前能做什么"
```

需要先配置：

```bash
export AZURE_OPENAI_API_KEY="..."
export AZURE_OPENAI_ENDPOINT="https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl"
export AZURE_OPENAI_API_VERSION="2024-03-01-preview"
export AZURE_OPENAI_DEPLOYMENT="..."
```

### 遗留问题

- `plan.md` 中的验收命令写的是 `python -m ...`，但当前环境只有 `python3`。
- 当前 trace 只记录一次运行的核心字段，Phase 2 再扩展 tool events、reflection 等完整结构。

### 下一个建议动作

- 配置真实模型环境变量后运行一次 CLI。
- 或进入 Phase 2：补充更完整的 Trace 与 Progress 记录。

---

## 2026-07-27 模型默认配置同步

### 本次要做

- 将办公网络 endpoint 配置为默认值。
- 将默认模型 deployment 配置为 `gpt-5.5-2026-04-24`。
- 保持 API key 只通过环境变量注入，不写入源码。

### 本次已完成

- 更新 `agent_lab/model/azure_client.py`：
  - 默认 endpoint：`https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl`
  - 默认 api version：`2024-03-01-preview`
  - 默认 deployment：`gpt-5.5-2026-04-24`
  - 必填环境变量收敛为 `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_VERSION`、`AZURE_OPENAI_DEPLOYMENT` 可选，设置后覆盖默认值。
- 新增 `.env.example`，只包含占位 key 和非敏感默认配置。
- 更新 `plan.md` 的默认模型配置说明。

### 关键说明

- API key 不决定访问哪个域名。
- 实际访问哪个模型服务网关由 `azure_endpoint` 决定。
- 当前默认会访问办公网络域名：

```text
https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl
```

- 如果显式设置 `AZURE_OPENAI_ENDPOINT=https://aidp-i18ntt-sg.byteintl.net/api/modelhub/online/v2/crawl`，则会改为访问 byteintl 域名。

### 验证命令和结果

```bash
python3 -m compileall agent_lab
```

结果：通过。

```bash
AZURE_OPENAI_API_KEY=dummy python3 - <<'PY'
from agent_lab.model.azure_client import AzureOpenAIConfig

config = AzureOpenAIConfig.from_env()
assert config.endpoint == 'https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl'
assert config.api_version == '2024-03-01-preview'
assert config.deployment == 'gpt-5.5-2026-04-24'
print(config.endpoint)
print(config.api_version)
print(config.deployment)
PY
```

结果：通过，默认 endpoint、api version、deployment 生效。

---

## 2026-07-27 Phase 2 开工记录

### 当前阶段

Phase 2：Trace 与 Progress 记录。

### 本次要做

- 扩展每次 agent 运行生成的 JSONL trace。
- trace 需要包含：
  - run id
  - user goal
  - prompt messages
  - model response
  - error
  - started_at / ended_at
  - tool events
  - reflection
- 确保成功和失败两种情况都会写入 trace。
- 保持 Phase 1 的 CLI 和最小 loop 用法兼容。

### 本次不会做

- 不实现真实 tool 调用。
- 不实现 context 模块。
- 不实现 memory recall。
- 不实现 evaluator 打分。
- 不实现多 agent。

### 本次已完成

- 扩展 `agent_lab/agent/state.py`：
  - 新增 `ToolEvent`，为后续 tool trace 预留结构。
  - `AgentRunResult` 新增 `tool_events` 字段。
  - `AgentRunResult` 新增 `reflection` 字段。
  - trace record 新增 `prompt_messages` 字段。
  - trace record 新增 `model_response` 字段。
  - 成功运行会生成基础 reflection。
  - 失败运行会记录 error 并生成失败 reflection。
- 保持 `assistant_answer` 字段兼容 Phase 1。
- 保持 `AgentLoop` 和 CLI 调用方式不变。
- 更新 `plan.md` Phase 2 状态。

### 修改文件

- `agent_lab/agent/state.py`
- `plan.md`
- `progress.md`

### 验证命令和结果

```bash
python3 -m compileall agent_lab
```

结果：通过，所有 Python 文件可编译。

```bash
python3 - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_lab.agent.loop import AgentLoop

class FakeModel:
    def complete(self, messages):
        return '这是一个测试回答。'

with TemporaryDirectory() as tmp:
    trace_file = Path(tmp) / 'agent_runs.jsonl'
    result = AgentLoop(FakeModel(), trace_file=trace_file).run('解释一下你当前能做什么')
    record = json.loads(trace_file.read_text(encoding='utf-8'))
    assert result.assistant_answer == '这是一个测试回答。'
    assert record['run_id'] == result.run_id
    assert record['user_goal'] == '解释一下你当前能做什么'
    assert record['prompt_messages'][0]['role'] == 'system'
    assert record['prompt_messages'][1]['role'] == 'user'
    assert record['model_response'] == '这是一个测试回答。'
    assert record['error'] is None
    assert record['started_at']
    assert record['ended_at']
    assert record['tool_events'] == []
    assert record['reflection']
    print('success trace ok')
PY
```

结果：通过，成功运行 trace 字段完整。

```bash
python3 - <<'PY'
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_lab.agent.loop import AgentLoop

class FailingModel:
    def complete(self, messages):
        raise RuntimeError('model unavailable')

with TemporaryDirectory() as tmp:
    trace_file = Path(tmp) / 'agent_runs.jsonl'
    try:
        AgentLoop(FailingModel(), trace_file=trace_file).run('测试失败 trace')
    except RuntimeError:
        pass
    else:
        raise AssertionError('expected RuntimeError')
    record = json.loads(trace_file.read_text(encoding='utf-8'))
    assert record['user_goal'] == '测试失败 trace'
    assert record['model_response'] is None
    assert record['assistant_answer'] is None
    assert record['error'] == 'RuntimeError: model unavailable'
    assert record['started_at']
    assert record['ended_at']
    assert record['tool_events'] == []
    assert '失败' in record['reflection']
    print('failure trace ok')
PY
```

结果：通过，失败运行也会写入 trace 并记录失败原因。

### 遗留问题

- 当前 `tool_events` 只是结构占位，还没有真实工具调用事件。
- 当前 `reflection` 是固定规则生成，不包含模型自评或 evaluator 打分。
- 当前没有独立测试文件，仍使用内联 smoke test 验证。

### 下一个建议动作

- 进入 Phase 3：实现 Context 模块，把 prompt/context 拼装从 `AgentLoop` 中拆出来。

## 2026-07-27 Phase 3 完成记录

### 本次目标

Phase 3：Context 模块。

目标：

- 将上下文拼装从 `AgentLoop` 中拆出来。
- 支持多个 context section：
  - system instruction。
  - runtime constraints。
  - memory。
  - tool descriptions。
- 为后续多轮对话保留 conversation history 接口。

### 设计结论

- 当前阶段不把 CLI 强制改成交互式循环。
- Context 模块只负责上下文组织，不负责读取用户输入或控制对话生命周期。
- 循环对话应放在 harness 层，例如后续增加 REPL CLI，由 harness 维护 history，再传给 `AgentLoop.run(..., conversation_history=...)`。

### 实现内容

- 新增 `agent_lab/context/manager.py`：
  - `ContextSection`：表示一个可渲染的上下文片段。
  - `ContextManager`：统一拼装 system context 和 prompt messages。
- 新增 `agent_lab/context/__init__.py`。
- 修改 `agent_lab/agent/loop.py`：
  - loop 不再直接拼接大段 prompt。
  - loop 通过 `ContextManager.build_messages()` 获取模型 messages。
  - 保持原有 `system_prompt` 入参兼容。
  - `run()` 支持可选 `conversation_history`。
- 新增测试：
  - `tests/test_context_manager.py`
  - `tests/test_agent_loop.py`

### 验证

```bash
python3 -m compileall agent_lab tests
```

结果：通过，所有源码和测试文件可编译。

```bash
python3 -m unittest discover -s tests
```

结果：通过，5 个测试全部成功。

### 遗留问题

- Context 裁剪、总结、优先级仍是后续扩展。
- Memory 和 Tool 目前只是 context section 的接入口，真实模块在 Phase 4/5 实现。
- CLI 仍是 one-shot；交互式循环可在后续 harness 扩展中实现。
