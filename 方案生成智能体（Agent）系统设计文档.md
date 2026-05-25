这是一份为您定制的**基于 LangGraph 与 LangChain Deep Agents 的方案生成智能体系统设计文档**。文档将前端的可视化编排、用户生成端与后端的状态图引擎、Deep Agents 自治内核进行了闭环整合，采用了规范的工程化结构进行呈现。

# 方案生成智能体（Agent）系统设计文档

## 1. 总体架构设计 (System Architecture)

本系统旨在打造一个由**数据/流程驱动、具备历史风格模仿与跨文档关系发现能力**的方案生成智能体。系统采用前后端分离架构，核心设计思想是将宏观的工作流控制（LangGraph）**与微观的**任务自治与技能调用（Deep Agents）相结合。

```
       ┌────────────────────────────────────────────────────────────────────────┐
       │                          前端系统 (Next.js / React)                     │
       │  ┌───────────────────────────────┐    ┌─────────────────────────────┐  │
       │  │     用户方案生成端 (前台)       │    │    开发者管理后台 (后台)     │  │
       │  └───────────────┬───────────────┘    └──────────────┬──────────────┘  │
       └──────────────────┼───────────────────────────────────┼─────────────────┘
                          │ (SSE 流式生成/事件通知)            │ (RESTful / JSON Config)
                          ▼                                   ▼
       ┌────────────────────────────────────────────────────────────────────────┐
       │                        后端核心引擎 (FastAPI / Python)                 │
       │  ┌──────────────────────────────────────────────────────────────────┐  │
       │  │                     LangGraph 工作流编排层                       │  │
       │  │   [START] ──> 数据检索 ──> 方案生成 ──> 一致性校验 ──> [END]     │  │
       │  └───────────────────────────────┬──────────────────────────────────┘  │
       │                                  │ (驱动 / 状态传递)                   │
       │  ┌───────────────────────────────▼──────────────────────────────────┐  │
       │  │                  Deep Agents 动态自治内核                         │  │
       │  │   ┌──────────────────────────────────────────────────────────┐   │  │
       │  │   │                虚拟文件系统 (Virtual VFS)               │   │  │
       │  │   └────────────┬───────────────┬─────────────────┬───────────┘   │  │
       │  │                ▼               ▼                 ▼               │  │
       │  │         [文件读写Skill]  [数据查询Skill]  [一致性检测Skill]       │  │
       │  └──────────────────────────────────────────────────────────────────┘  │
       └────────────────────────────────────────────────────────────────────────┘
```

## 2. 前端系统设计 (Frontend Design)

前端采用 **Next.js (React) + Tailwind CSS + Shadcn UI** 核心技术栈，分为“前台生成端”与“后台管理端”。

### 2.1 技术选型与理由

| **模块**         | **推荐选型**               | **选用理由**                                                 |
| ---------------- | -------------------------- | ------------------------------------------------------------ |
| **应用基础框架** | **Next.js (React)**        | 全球 AI/Agent 开源生态（Vercel AI SDK）的绝对中心，便于快速集成大模型流式组件。 |
| **流程编排画布** | **React Flow**             | 极其成熟的低代码节点连线库，无缝映射 LangGraph 的图结构（Nodes & Edges）。 |
| **流式交互组件** | **Vercel AI SDK**          | 原生支持流式响应（SSE）与中间推理步骤（Thought/Reasoning）的流式渲染。 |
| **文档编辑器**   | **Monaco Editor / TipTap** | 支持 Markdown 语法高亮、实时 Diff 对比、代码/参数标记。      |

### 2.2 用户前端：用户方案生成端功能设计

1. **需求向导舱（Wizard Form）**：采用多步骤表单引导用户输入场景参数（如：易燃场所、联动设备范围）、导入基础物料，并支持“一键克隆”历史优秀方案作为写作风格模版。
2. **生成动态看板（Graph Monitor）**：利用 SSE（Server-Sent Events）订阅后端的事件流。左侧以时间轴/流式状态卡片展示后端 Agent 的执行进度（如：*“🔍 正在检索资产特征库...”* -> *“✍️ Writer Agent 正在模仿生成第2章...”*）；右侧为打字机式的方案预览区。
3. **方案工作台（Editor Workplace）**：方案生成完成后自动转换为 Markdown 可编辑状态，提供 AI 辅助润色功能，并包含 “AI 原始版本 vs 用户修改版本”的差异对比（Diff 视图）。
4. **人机反馈组件（HITL Feed）**：用户在微调文本后，可点击“反哺库”按钮，将修改后的片段作为高质量 Few-shot 数据异步写入后端知识库。

### 2.3 开发人员前端：开发者管理系统功能设计

1. **技能仓（Skill Hub）**：支持对 Deep Agents 的 Skill 进行可视化管理。
   - **配置界面**：支持在线填写或修改 `SKILL.md` 的 YAML 元数据（名称、描述、入参 JSON Schema）。
   - **热加载开关**：一键启用/禁用特定 Skill，直接影响后端的动态挂载逻辑。
2. **流程编排画布（Flow Builder）**：基于 React Flow 打造低代码画布。
   - 开发者可拖拽“数据分割”、“图谱检索”、“LLM编写”、“一致性校验”等节点并进行连线。
   - 双击节点可在右侧侧边栏配置其业务参数（如调整 RAG 检索的特征分值、Top-K 权重等）。
   - 画布支持一键导出为标准的拓扑结构 JSON 串，下发至后端。

## 3. 后端系统设计 (Backend Design)

后端基于 **FastAPI + LangGraph + LangChain DeepAgents** 构建，将宏观业务流的稳定性与微观大模型的动态自治完美结合。

### 3.1 全局状态设计 (Graph State)

在 LangGraph 中定义统一的 `AgentState` 结构体，用于在节点、Skill 与工具之间高频传递上下文与中间文件指针。

Python

```
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]        # 基础对话与推理日志链
    business_context: Dict[str, Any]               # 前端输入的业务参数（如场景特征、阈值分数）
    virtual_files: Dict[str, str]                  # 虚拟文件系统指针 (文件名 -> 存储路径/Hash)
    consistency_report: Dict[str, Any]             # 文档一致性与合规性校验报告
    generated_charts: List[Dict[str, Any]]          # 图表数据组件清单
```

### 3.2 核心技能（Skill）与工具（Tool）设计

基于 Deep Agents 的 **“渐进式披露”** 机制，将复杂业务拆分为自治的 Skill 文件夹（包含 `SKILL.md` 与驱动脚本）。

#### ① 读写文件技能 (`skills/file-ops/`)

- **职责**：对接虚拟文件系统（VFS），处理超长文本分块写入与多章节合并，避免大模型因单次生成篇幅过长导致的内容截断或 Token 爆炸。

- **元数据声明 (`SKILL.md`)**：

  YAML

  ```
  name: plan-file-manager
  description: 用于方案大纲、章节草稿、 Few-shot 样例文件的读写、追加和暂存。
  allowed_tools: [read_file, write_file, edit_file]
  ```

#### ② 数据查询技能 (`skills/data-query/`)

- **职责**：接收业务场景参数，检索资产库或关系图数据库（Neo4j），抽取设备联动特征标签与风险评级分值，并格式化为高密度的 Markdown 表格注入上下文。
- **元数据声明 (`SKILL.md`)**：

YAML

```
    name: business-data-query
    description: 实时查询防范领域设备特征值、场所风险等级及联动逻辑，提供方案编写的硬性事实依据。
```

#### ③ 文档一致性检测技能 (`skills/consistency-checker/`)
*   **职责**：提取方案文本中的核心参数，与 `business_context` 中的原始业务数据进行交叉比对。若发现数据冲突（如：方案描述部署 3 台设备，但资产库硬性要求为 5 台），则触发打回重写逻辑。
*   **元数据声明 (`SKILL.md`)**：
    

```yaml
    name: consistency-checker
    description: 自动化提取已生成文本中的技术指标与合规标准，进行严格的忠实度（Groundedness）与一致性核对。
    ```

#### ④ 图表生成工具 (LangChain `@tool`)
*   **职责**：确定性的原子化数据可视化工具。接收结构化数据，调用 `matplotlib` 渲染图表并存入虚拟文件系统，返回路径供前端展示。
​```python
from langchain_core.tools import tool
import matplotlib.pyplot as plt

@tool
def generate_asset_chart(chart_type: str, data_points: list[dict]) -> str:
    """根据传入的资产或风险数据绘制图表。chart_type 可选 'bar' 或 'pie'。
    返回图表在虚拟文件系统中的存储路径。
    """
    plt.figure(figsize=(6, 4))
    x = [d['label'] for d in data_points]
    y = [d['value'] for d in data_points]
    
    if chart_type == 'bar': plt.bar(x, y, color='skyblue')
    elif chart_type == 'pie': plt.pie(y, labels=x, autopct='%1.1f%%')
        
    file_path = f"/workspace/charts/output_{chart_type}.png"
    plt.savefig(file_path, format='png')
    plt.close()
    return f"图表生成成功: {file_path}"
```

## 4. 前后端协同与工作流编排 (Workflow Implementation)

系统通过 LangGraph 编排宏观状态节点。在核心的编写与校验节点内，动态挂载 Deep Agents 并通过 `stream_events` 机制向前端流式下发 Ergonomic Projections（标准事件投影）。

### 4.1 后端核心编排引擎实现

Python

```
from langgraph.graph import StateGraph, START, END
from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

# 1. 初始化模型与自治体内核
model = ChatOpenAI(model="gpt-4o", streaming=True)

# 动态组装自治智能体，注入技能仓
plan_agent_kernel = create_deep_agent(
    model=model,
    tools=[generate_asset_chart],
    skills=["./skills/file-ops", "./skills/data-query", "./skills/consistency-checker"],
    system_prompt="你是一个防范方案编写专家。请充分利用 data-query 获取事实，严格执行 consistency-checker 校验内容。"
)

# 2. 定义 LangGraph 节点行为
def research_stage(state: AgentState):
    """[数据检索阶段]"""
    response = plan_agent_kernel.invoke({
        "messages": [("user", f"请查询场景 {state['business_context']['scene']} 下的设备特征值并写入临时文件区。")]
    })
    return {"messages": [response]}

def generation_stage(state: AgentState):
    """[章节模仿生成阶段] - 引入 Few-shot 约束"""
    response = plan_agent_kernel.invoke({
        "messages": [("user", "请参照历史优秀方案的编写风格，为该场景生成‘风险识别与设备部署’章节，确保字数在1500字以上。")]
    })
    return {"messages": [response]}

def validation_stage(state: AgentState):
    """[双向校验阶段]"""
    response = plan_agent_kernel.invoke({
        "messages": [("user", "调用 consistency-checker 技能，核对已生成文档的参数与资产库是否对齐。")]
    })
    return {"messages": [response]}

# 3. 构建拓扑结构与条件路由
workflow = StateGraph(AgentState)
workflow.add_node("DataResearch", research_and_query_node)
workflow.add_node("PlanGeneration", generation_loop_node)
workflow.add_node("CriticValidation", validation_node)

workflow.add_edge(START, "DataResearch")
workflow.add_edge("DataResearch", "PlanGeneration")
workflow.add_edge("PlanGeneration", "CriticValidation")

def route_decision(state: AgentState):
    """条件路由：根据校验结果决定结束或退回重写"""
    if "校验失败" in state["messages"][-1].content:
        return "PlanGeneration" # 携带错误日志退回，重新生成当前章节
    return END

workflow.add_conditional_edges("CriticValidation", route_decision)
app = workflow.compile()
```

## 5. 前后端数据交互协议 (API & Streaming Protocols)

### 5.1 后台发布/更新 Skill 协议 (RESTful JSON)

- **请求**：`POST /api/v1/skills/update`
- **Body**：

JSON

```
    {
      "skill_id": "consistency-checker",
      "meta_yaml": "name: consistency-checker\ndescription: 自动化提取技术指标...",
      "script_code": "def verify_alignment(generated_text, source_data):\n..."
    }
    ```
*   **后端处理**：后端接收后，将其持久化并动态写入对应的本地/云端技能文件夹，当下次用户触发生成任务时，新逻辑自动生效（热加载）。

### 5.2 前台流式生成协议 (SSE Stream Events v3)
当用户点击“开始生成方案”时，前端通过 EventSource 或 Fetch 建立 SSE 连接。后端执行 `app.stream_events`，向前端实时推送结构化事件。

#### 交互事件流示例：
1.  **触发数据检索时**：
    

```json
    event: agent_event
    data: {"type": "on_skill_start", "name": "business-data-query", "message": "正在查询资产特征数据库..."}
    ```
2.  **触发图表生成时**：
    

```json
    event: agent_event
    data: {"type": "on_tool_start", "name": "generate_asset_chart", "message": "正在绘制联动效率柱状图..."}
    ```
3.  **文本流式生成（打字机效果）**：
    

```json
    event: text_delta
    data: {"type": "on_message_delta", "content": "1.1 风险识别\n通过对该防范区域进行特征值抽取..."}
    ```
4.  **校验未通过重判时**：
    

```json
    event: agent_event
    data: {"type": "on_skill_failed", "name": "consistency-checker", "message": "检测到参数不一致！方案描述与设备库冲突，正在打回重新生成..."}
    ```

---

> **💡 架构演进建议**
> 在系统上线初期，可以先让后端的 Skill 目录保持静态（代码托管），前台优先打通 SSE 流式生成和 Markdown 编辑工作台。稳定后，再开放后台的低代码配置和 `SKILL.md` 的可视化热加载，以实现资产的完全无代码维护。

```

```