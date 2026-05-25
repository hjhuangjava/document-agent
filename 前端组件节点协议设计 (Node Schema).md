##  前端组件节点协议设计 (Node Schema)

在前端（如使用 React Flow）中，每一个组件（节点）本质上是一个 JSON 对象。为了让组件支持“下拉选择”、“连线”和“输入输出配置”，我们需要定义如下的统一数据结构：

JSON

```
{
  "component_type": "DATA_QUERY_SKILL", 
  "name": "资产数据查询组件",
  "description": "根据场景标签，从MySQL或资产库中捞取设备特征和联动分值。",
  "inputs": [
    { "name": "scene_id", "type": "string", "required": true, "description": "场景唯一标识" },
    { "name": "min_score", "type": "number", "default": 60, "description": "特征分值过滤下限" }
  ],
  "outputs": [
    { "name": "device_table_md", "type": "string", "description": "Markdown格式的设备特征表" },
    { "name": "raw_json_data", "type": "json", "description": "原始业务结构化数据" }
  ]
}
```

## 二、 前端页面功能设计

根据你的设想，前端开发者管理后台的画布页面可以划分为**三个核心区域**：

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Agent 流程编排看板 (React Flow)                  │
├──────────────────────┬──────────────────────────┬──────────────────────┤
│                      │                          │                      │
│  【1. 左侧组件面板】  │   【2. 中央连线画布】    │ 【3. 右侧参数配置窗】│
│                      │                          │                      │
│ ┌──────────────────┐ │   ┌──────────────┐       │ ┌──────────────────┐ │
│ │  数据处理组件    │ │   │ 数据查询组件 │       │ │ 节点：数据查询组件│ │
│ │  ├─ 资产数据查询  │ │   │  [in] ───────┼──┐    │ │                  │ │
│ │  └─ PDF多模态解析 │ │   └──────────────┘  │    │ │ 输入参数配置：   │ │
│ │                  │ │                     ▼    │ │ - scene_id:     │ │
│ │  核心生成组件    │ │              ┌──────────────┐│ │   [ 选择State ]  │ │
│ │  ├─ 模仿编写器    │ │              │ 模仿编写器   ││ │ - min_score:    │ │
│ │  └─ 图表渲染器    │ │              │  [out] ──────││ │   [ 80        ]  │ │
│ │                  │ │              └──────────────┘│ │                  │ │
│ │  校验/质量组件   │ │                          │ │ 触发条件：       │ │
│ │  └─ 一致性检测   │ │                          │ │ - score > 80     │ │
│ └──────────────────┘ │                          │ └──────────────────┘ │
│                      │                          │                      │
└──────────────────────┴──────────────────────────┴──────────────────────┘
```

### 1. 左侧组件面板（Component Palette）

- **分组下拉/折叠列表**：将你后端的 Skill 和 Tool 归类展示。
  - *数据源组件*：资产数据查询、PDF多模态解析、历史方案库检索。
  - *执行生成组件*：大纲规划器、长文本模仿编写器、ECharts 图表渲染器。
  - *质量校验组件*：一致性检测器、合规性断言器（Code Interpreter）。
- **交互动作**：支持用户将组件从左侧拖拽（Drag & Drop）到中央画布中，松开鼠标即生成一个画布节点。

### 2. 中央连线画布（Visual Canvas）

- **Handle（连接点）管理**：
  - 节点的左侧或上方根据 `inputs` 数量渲染多个**输入连接点（Target Handle）**。
  - 节点的右侧或下方根据 `outputs` 数量渲染多个**输出连接点（Source Handle）**。
- **连线规则约束（Validation）**：
  - 前端需要做类型强校验（Type Matching）。例如：一个输出 `type: "image_path"` 的连接点，**禁止**连线到只接收 `type: "number"` 的输入连接点上。
  - 支持**条件分支连线（Conditional Edge）**：从“一致性检测组件”出来两条线，一条连线标记为 `is_valid == true` 指向结束，另一条标记为 `is_valid == false` 指向重新生成。

### 3. 右侧参数配置窗（Property Inspector）

当用户点击画布上的某个节点时，右侧弹出该节点的属性配置面板：

- **输入映射（Input Mapping）**：用户可以选择该输入的赋值方式：
  1. **静态固定值**：直接在输入框里填死（如 `min_score = 80`）。
  2. **动态绑定全局状态**：通过下拉菜单，绑定到全局的 `Graph State`（例如 `scene_id` 绑定到前端传入的 `state.business_context.scene`）。
- **输出去向（Output Binding）**：配置该节点的输出应该写入到全局 `Graph State` 的哪个字段中，以便后续节点读取。

## 三、 前后端的核心桥接逻辑：从“图”到“代码”

前端拖拽连线完成后，点击“保存并发布”，前端会将全图的数据结构导出为一个拓扑 JSON 串发送给 FastAPI 后端。

### 1. 前端生成的拓扑 JSON 样例

JSON

```
{
  "workflow_id": "flow_plan_generation_001",
  "nodes": [
    { "id": "node_1", "type": "DATA_QUERY_SKILL", "data": { "min_score": 80 } },
    { "id": "node_2", "type": "WRITER_SKILL", "data": { "style_template": "premium" } }
  ],
  "edges": [
    {
      "source": "node_1",
      "sourceHandle": "device_table_md",
      "target": "node_2",
      "targetHandle": "context_data"
    }
  ]
}
```

### 2. 后端解析器（Graph Interpreter）的运行机制

后端的 LangGraph 并不需要每次都动态去拼接 Python 代码，而是使用一个**通用的图解释器节点**：

Python

```
def universal_node_executor(node_id: str, current_state: AgentState):
    """一个通用的 LangGraph 节点，用来解析并执行前端配置的组件"""
    # 1. 从数据库/内存中读取前端下发的 workflow JSON 配置
    node_config = get_node_config_by_id(node_id)
    
    # 2. 准备组件的输入 (将前端配置的静态值或 State 映射值组装起来)
    resolved_inputs = {}
    for inp in node_config["inputs"]:
        if inp["bind_type"] == "state":
            resolved_inputs[inp["name"]] = current_state.get(inp["state_key"])
        else:
            resolved_inputs[inp["name"]] = inp["static_value"]
            
    # 3. 根据组件类型，动态调度 Deep Agents 内核或具体 Skill
    # Deep Agents 接收 resolved_inputs 执行文件读写、数据查询或校验
    execution_result = plan_agent_kernel.execute_skill(
        skill_name=node_config["component_type"], 
        inputs=resolved_inputs
    )
    
    # 4. 根据前端配置的输出映射，更新全局 LangGraph State 并返回
    state_updates = {}
    for out in node_config["outputs"]:
        state_key = out["bind_state_key"]
        state_updates[state_key] = execution_result.get(out["name"])
        
    return state_updates
```

通过这种设计，你的前端就变成了一个功能完备的 **Agent IDE（集成开发环境）**。开发人员只需要在线开发新的 `Skill.md`（定义好输入输出），前端的组件列表就会自动刷新，接着就能通过拖拽连线，立刻组装出全新的防范方案生成工作流，完全实现了**无代码/低代码的业务敏捷交付**。





在实际开发中，前端和后端的分工是极其明确的：

| **阶段**        | **后端（LangGraph）干什么**                                  | **前端（React Flow）干什么**                                 |
| --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **1. 流程编译** | **解析拓扑结构：** 接收前端发来的节点和边，编译成 Python/TS 的 StateGraph，检查有没有环路、死循环。 | **画看板：** 允许用户拖拽、连线、配置每个节点的参数（比如 prompt、温度），最后打包成一个 JSON 字典发给后端。 |
| **2. 运行时**   | **真正的执行者：** 1. 维护全局状态（State）。 2. 调用 LLM（大模型）。 3. 运行 Tool（工具）。 4. 决定下一步走哪个分支（Conditional Edge）。 | **听话的传声筒：** 1. 监听后端发来的消息（通过 WebSocket 或 SSE 流式传输）。 2. 收到“当前正在跑 Agent 节点”的消息后，让前端画布上的 Agent 节点闪烁、亮起。 |
| **3. 人类介入** | **暂停与等待：** 执行到敏感节点（如发邮件）时中断运行，保持当前 Checkpoint（检查点），等待外部信号。 | **交互界面：** 发现后端暂停了，就在对应的节点上弹出一个漂亮的确认框，让用户点“同意”或“拒绝”，把信号发回后端。 |

你只需要记住：**所有关于“图的跳转逻辑”、“AI 怎么思考”、“工具怎么运行”的代码全部写在后端（LangGraph）。**

前端的 React Flow 只干两件事：**要么把后端的执行进度“画”出来给用户看，要么把用户的拖拽结果变成数据“提”给后端。**