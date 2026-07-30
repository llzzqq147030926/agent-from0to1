# Self-Training Agent Plan

## 目标

实现一个可逐步演进的 agent 系统，从最小 agent loop 开始，逐步加入 context、memory、tool、self-optimization、training data export、多 agent 等模块。

第一阶段不直接追求复杂训练框架，而是先建立稳定的运行闭环：

1. agent 能接收目标并生成输出。
2. agent 能记录过程、结果和失败原因。
3. agent 能通过反思和评估产生可复用经验。
4. agent 能把成功/失败样本沉淀为未来优化模型的数据。

## 设计原则

### 核心能力模块化

agent 的核心能力按模块拆分，避免把所有逻辑塞进一个 loop：

- loop：负责单轮/多轮执行编排。
- context：负责上下文组织、压缩、裁剪。
- memory：负责长期经验存储和召回。
- tools：负责外部能力调用。
- evaluator：负责结果评价。
- reflection：负责自我复盘。
- trainer/exporter：负责把运行轨迹转为训练数据。
- multi-agent：负责多角色协作。

### Harness 独立

运行环境和核心能力分离：

- CLI、脚本、服务入口属于 harness。
- agent loop、model client、tool registry 等属于核心模块。
- 后续可以在不改核心逻辑的情况下切换 CLI、API server、notebook 或任务队列。

### 严格契约

对模型输出、工具参数、训练样本格式采用严格校验：

- 缺少必要字段直接报错。
- tool 参数不合法直接报错。
- 模型输出不符合预期结构时记录失败样本。
- 不做静默降级，避免 pipeline 错误被掩盖。

### 密钥与模型配置

模型配置通过环境变量注入，不写死在代码里。

用户提供的 Azure OpenAI 兼容配置：

```python
import openai

client = openai.AzureOpenAI(
    api_key="通过环境变量注入",
    azure_endpoint="https://aidp-i18ntt-sg.byteintl.net/api/modelhub/online/v2/crawl",
    api_version="2024-03-01-preview",
)
```

办公网络下 endpoint 需要改为：

```text
https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl
```

默认模型配置：

```bash
AZURE_OPENAI_ENDPOINT=https://aidp-i18ntt-sg.tiktok-row.net/api/modelhub/online/v2/crawl
AZURE_OPENAI_API_VERSION=2024-03-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.5-2026-04-24
```

运行时仍可通过环境变量覆盖 endpoint、api version、deployment。API key 必须通过环境变量注入。

计划使用的环境变量：

```bash
AZURE_OPENAI_API_KEY
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_API_VERSION
AZURE_OPENAI_DEPLOYMENT
```

## 目标架构

```text
agent_lab/
  agent/
    loop.py              # agent loop，控制一次任务执行生命周期
    state.py             # 运行状态、trace、step 结构
    messages.py          # message 契约与转换

  model/
    azure_client.py      # Azure OpenAI 兼容模型客户端
    protocol.py          # 模型接口协议

  context/
    manager.py           # context 拼装、裁剪、压缩
    sections.py          # system/user/memory/tool 等上下文区块

  memory/
    store.py             # memory 抽象接口
    jsonl_store.py       # 本地 JSONL 存储
    recall.py            # 召回策略

  tools/
    base.py              # tool 协议、参数校验、registry
    web.py               # URL 访问工具
    github.py            # GitHub 访问工具

  optimize/
    evaluator.py         # 输出评价
    reflection.py        # 自我复盘
    trace_exporter.py    # 训练数据导出

  multi_agent/
    roles.py             # planner / executor / critic 等角色定义
    orchestrator.py      # 多 agent 编排

  harness/
    cli.py               # 命令行入口
```

## 分阶段计划

### Phase 0：文档与边界定义

产物：

- `plan.md`
- `progress.md`

目标：

- 明确项目目标。
- 明确模块边界。
- 明确逐步实现顺序。
- 先不写代码，等待用户逐步确认。

状态：已完成。

### Phase 1：最小 Agent Loop

目标：

- 实现一个最小可运行 agent。
- 输入用户目标。
- 拼装 system prompt 和 user message。
- 调用模型。
- 输出 assistant answer。
- 记录一次运行结果。

暂不实现：

- 自动 tool call。
- 长期 memory recall。
- 多 agent。
- 训练任务。

验收：

```bash
python -m agent_lab.harness.cli "解释一下你当前能做什么"
```

预期：

- 能调用模型并返回结果。
- 本地生成一条运行记录。

状态：已完成最小代码实现。当前环境没有 `python` 命令，已使用 `python3` 完成编译、假模型 loop、CLI help 验证。真实模型调用需要先配置 `AZURE_OPENAI_*` 环境变量。

### Phase 2：Trace 与 Progress 记录

目标：

- 每次 agent 运行都记录 trace。
- trace 包含：
  - run id
  - user goal
  - prompt messages
  - model response
  - error
  - started_at / ended_at
  - tool events
  - reflection

验收：

- 每次运行后都有 JSONL trace。
- 出错时也能记录失败原因。

状态：已完成基础 trace 扩展。当前 trace 已包含 run id、user goal、prompt messages、model response、error、started_at、ended_at、tool events、reflection。tool events 目前为空列表，等待 Phase 5 接入真实工具调用。

### Phase 3：Context 模块

目标：

- 将上下文拼装从 loop 中拆出来。
- 支持多个 context section：
  - task
  - system instruction
  - memory
  - tool descriptions
  - runtime constraints

后续扩展：

- context 裁剪。
- context 总结。
- context 优先级。

验收：

- loop 不直接拼大段 prompt。
- context manager 可单独测试。

状态：已完成基础 Context 模块。`AgentLoop` 已改为通过 `ContextManager` 生成 prompt messages，Context 支持 system instruction、runtime constraints、memory、tool descriptions 以及 conversation history。当前 CLI 仍保持 one-shot；循环对话应作为 harness 层扩展接入，不放进 Context 模块本身。

### Phase 4：Memory 模块

目标：

- 先实现本地 JSONL memory。
- 支持 append。
- 支持简单关键词 recall。
- 保存 agent 自我反思结果。

后续扩展：

- embedding recall。
- vector store。
- memory importance score。
- memory decay。

验收：

- agent 能读取历史经验。
- agent 能把本次经验写回 memory。

### Phase 5：Tool 系统

目标：

- 实现 tool protocol。
- 实现 tool registry。
- 实现严格参数校验。
- 增加第一批工具：
  - `fetch_url`：访问网页。
  - `github_repo_info`：读取 GitHub repo 元信息。
  - `github_file`：读取 GitHub 文件内容。

设计重点：

- tool 需要有 name、description、input schema、handler。
- tool 失败需要进入 trace。
- tool 输入输出都要可序列化。

验收：

- 可以独立调用工具。
- agent loop 可以看到可用工具描述。
- 后续再接入模型自动选择工具。

### Phase 6：Tool-Calling Agent Loop

目标：

- 让模型能选择工具。
- agent 执行工具并把 observation 回填给模型。
- 支持最多 N 步循环，避免无限调用。

执行模式：

```text
user goal
  -> model decides answer or tool call
  -> run tool
  -> append observation
  -> model continues
  -> final answer
```

验收：

- agent 能为了回答问题访问 URL。
- agent 能为了理解代码访问 GitHub repo/file。

### Phase 7：Evaluator 与 Reflection

目标：

- 增加自我评价模块。
- 对每次运行生成结构化评价：
  - 是否完成目标
  - 是否使用了必要工具
  - 是否出现错误
  - 输出是否遵循格式
  - 下一次应如何改进

验收：

- 每次 trace 都有 evaluator result。
- 每次 trace 都有 reflection note。
- reflection 能写入 memory。

### Phase 8：Self-Optimization 数据闭环

目标：

- 将高质量 trace 导出为训练样本。
- 将失败 trace 导出为纠错样本。
- 建立 dataset schema。

训练样本初始格式：

```json
{
  "goal": "...",
  "context": "...",
  "tool_events": [],
  "final_answer": "...",
  "score": 0.0,
  "reflection": "..."
}
```

验收：

- 可以从 traces 生成 JSONL dataset。
- dataset 生成前执行严格 schema 校验。

### Phase 9：多 Agent

目标：

- 在单 agent 稳定后引入多 agent。
- 第一批角色：
  - planner：拆解任务。
  - executor：执行工具和代码。
  - critic：审查结果。
  - researcher：独立收集信息。

原则：

- 先串行，后并行。
- 只有互相独立的研究任务才并行。
- 所有 agent 共享 trace，但保留各自 scratchpad。

验收：

- 能完成 planner -> executor -> critic 的基础链路。
- critic 的反馈能进入下一轮优化。

## 当前已实现的内容

当前已完成：

- `plan.md`
- `progress.md`
- 最小 Python 包结构 `agent_lab/`
- message 契约
- run state 与 JSONL trace 序列化
- 成功/失败 trace 记录
- trace 字段扩展：
  - run id
  - user goal
  - prompt messages
  - model response
  - error
  - started_at / ended_at
  - tool events
  - reflection
- one-shot agent loop
- Azure OpenAI 兼容模型客户端
- CLI harness
- `requirements.txt`

当前仍未实现：

- 自动 tool call。
- 长期 memory recall。
- 多 agent。
- 训练任务。
- 真实模型调用验证。

后续建议进入 Phase 3：Context 模块，或先配置真实模型环境变量运行一次 Phase 1 CLI。
