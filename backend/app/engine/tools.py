"""Tool registry – all @tool functions live here. No dynamic code execution."""

import uuid

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for servers
import matplotlib.pyplot as plt
from langchain_core.tools import tool

from app.engine.vfs import VirtualFileSystem

# ---------------------------------------------------------------------------
# Mock knowledge base (used by knowledge_search tool)
# ---------------------------------------------------------------------------

MOCK_DOCS: list[dict] = [
    {
        "id": "kb_001",
        "title": "Q3 季度销售报告",
        "content": (
            "2024年Q3季度总销售额达到2.3亿元，同比增长15.2%。"
            "华东区域表现突出，贡献了总营收的42%，华南区域增长最快达22%。"
            "主力产品线A系列销量突破10万件，B系列新品上市首月即完成5000件。"
        ),
        "score": 0.0,
        "source": "销售部/季度报告/Q3_2024_报告.pdf",
        "category": "报告",
        "updated_at": "2024-10-15 14:30:00",
    },
    {
        "id": "kb_002",
        "title": "产品需求规格说明书 v2.3",
        "content": (
            "本文档定义文档智能生成平台 v2.3 的功能需求。"
            "核心模块包括：知识库检索、工作流编排引擎、多格式文档生成（PDF/Word/HTML）、"
            "AI辅助内容校对。支持通过自然语言描述业务场景，自动生成专业方案文档。"
        ),
        "score": 0.0,
        "source": "产品部/PRD/平台_v2.3.docx",
        "category": "文档",
        "updated_at": "2024-09-28 10:00:00",
    },
    {
        "id": "kb_003",
        "title": "数据安全与合规管理办法",
        "content": (
            "第一条 为规范公司数据处理活动，保障数据安全，根据《数据安全法》《个人信息保护法》制定。"
            "第二条 数据分类分级：核心数据、重要数据、一般数据。核心数据存储须加密，访问须审批。"
            "第三条 数据出境须经安全评估，不得将核心数据存储在境外服务器。"
        ),
        "score": 0.0,
        "source": "法务部/制度/数据安全管理办法_v1.0.pdf",
        "category": "制度",
        "updated_at": "2024-08-20 09:00:00",
    },
    {
        "id": "kb_004",
        "title": "华东大客户拓展方案",
        "content": (
            "目标：2025年Q1在华东区域新增3家战略级客户，目标合同金额不低于5000万元。"
            "策略：1) 聚焦金融、政务两大行业；2) 联合ISV生态伙伴共建解决方案；"
            "3) 投入专项售前资源2人，POC周期压缩至2周。"
        ),
        "score": 0.0,
        "source": "销售部/方案/华东大客户拓展方案_2025.pptx",
        "category": "方案",
        "updated_at": "2024-11-05 16:00:00",
    },
    {
        "id": "kb_005",
        "title": "智能文档平台技术白皮书",
        "content": (
            "本平台基于LangGraph工作流引擎，支持可视化编排Agent和Tool节点。"
            "架构采用FastAPI + React + PostgreSQL，支持SSE实时推送执行状态。"
            "内置知识库检索、图表生成、文档排版等20+可配置工具。"
            "LLM层适配OpenAI兼容接口，支持DeepSeek、Moonshot等国产模型。"
        ),
        "score": 0.0,
        "source": "技术部/白皮书/智能文档平台_v1.0.pdf",
        "category": "文档",
        "updated_at": "2024-10-01 11:00:00",
    },
    {
        "id": "kb_006",
        "title": "年度员工培训计划",
        "content": (
            "2025年度培训预算总计120万元，覆盖全员500人。"
            "重点方向：AI工具应用（40%）、项目管理（25%）、行业知识（20%）、领导力（15%）。"
            "Q1启动「AI效率提升」专项，要求全员通过AI工具认证考核。"
        ),
        "score": 0.0,
        "source": "HR/计划/2025培训计划.xlsx",
        "category": "计划",
        "updated_at": "2024-12-01 08:30:00",
    },
    {
        "id": "kb_007",
        "title": "合同评审标准流程",
        "content": (
            "合同金额≤50万：销售总监审批；50-200万：VP审批；＞200万：CEO审批。"
            "所有合同须经法务评审，风险等级分低/中/高三档。"
            "高风险条款包括：无限赔偿责任、知识产权归属不清、数据条款不符合GDPR要求。"
        ),
        "score": 0.0,
        "source": "法务部/流程/合同评审流程_v3.1.pdf",
        "category": "制度",
        "updated_at": "2024-07-15 13:00:00",
    },
    {
        "id": "kb_008",
        "title": "竞品分析：文档生成赛道",
        "content": (
            "主要竞品：Notion AI（文档+协作）、Gamma（演示文稿AI）、Jasper（营销文案）。"
            "我们的差异化优势：1) 深度集成企业内部知识库；2) LangGraph流程可编排；"
            "3) 支持国产大模型私有化部署。价格方面对标Notion AI的$10/月，定价9.9元/月。"
        ),
        "score": 0.0,
        "source": "产品部/竞品分析/文档生成赛道_2024.pdf",
        "category": "报告",
        "updated_at": "2024-11-20 15:00:00",
    },
]

def _simple_search(query: str, docs: list[dict], top_k: int) -> list[dict]:
    """Match documents by keyword overlap and return scored results."""
    query_lower = query.lower()
    scored = []

    for doc in docs:
        text = (doc["title"] + doc["content"]).lower()
        score = 0.0
        for word in query_lower.split():
            if len(word) >= 2 and word in text:
                score += 1.0 / len(query_lower.split())
        if score > 0:
            scored.append({**doc, "score": round(min(score, 1.0), 4)})

    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored[:top_k]


def _get_state_path(state: dict, path: str):
    keys = path.split(".")
    cur = state
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def _set_state_path(updates: dict, path: str, value):
    keys = path.split(".")
    cur = updates
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _resolve_value(state: dict, binding: dict):
    bind = binding.get("bind", {})
    if bind.get("type") == "state":
        state_key = bind.get("state_key") or binding["name"]
        return _get_state_path(state, state_key)
    return bind.get("value", binding.get("default"))


def _resolve_inputs(state: dict, input_bindings: list[dict], tool_name: str) -> dict:
    resolved: dict = {}
    for b in input_bindings:
        val = _resolve_value(state, b)
        if val is None:
            val = b.get("default")
        resolved[b["name"]] = val
    return resolved


def _bind_outputs(result, output_bindings: list[dict] | None, default_output_name: str = "result") -> dict:
    state_updates: dict = {}
    output_bindings = output_bindings or []
    if not output_bindings:
        if isinstance(result, dict):
            return result
        return {default_output_name: result}
    if len(output_bindings) == 1:
        ob = output_bindings[0]
        output_name = ob["output_name"]
        state_key = ob.get("state_key") or output_name
        state_updates[state_key] = result
    else:
        for ob in output_bindings:
            output_name = ob["output_name"]
            state_key = ob.get("state_key") or output_name
            value = result.get(output_name) if isinstance(result, dict) else result
            _set_state_path(state_updates, state_key, value)
    return state_updates

# ---------------------------------------------------------------------------
# Session-level VFS cache (keyed by session_id)
# ---------------------------------------------------------------------------
_vfs_cache: dict[str, VirtualFileSystem] = {}


def get_vfs(session_id: str) -> VirtualFileSystem:
    if session_id not in _vfs_cache:
        _vfs_cache[session_id] = VirtualFileSystem(session_id=session_id)
    return _vfs_cache[session_id]


def release_vfs(session_id: str):
    vfs = _vfs_cache.pop(session_id, None)
    if vfs:
        vfs.cleanup()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

@tool
async def query_business_data(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """查询资产特征库，返回设备特征、风险等级及联动逻辑。"""
    resolved = _resolve_inputs(state, input_bindings, "query_business_data")
    output02 = resolved.get("output02", [])
    min_score = resolved.get("min_score", 60) or 60
    result = (
        "| 设备名称 | 特征分值 | 风险等级 |\n"
        "|----------|----------|----------|\n"
        f"| 示例设备A | 85 | 高 |\n"
        f"| 示例设备B | {min_score} | 中 |\n"
    )
    return _bind_outputs(result, output_bindings)


@tool
async def check_consistency(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """核对方案原文与业务数据的一致性。"""
    _resolve_inputs(state, input_bindings, "check_consistency")
    result = {"validation_result": {"status": "pass", "violations": []}}
    return _bind_outputs(result, output_bindings)


@tool
async def generate_chart(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """绘制图表并存入 VFS。"""
    resolved = _resolve_inputs(state, input_bindings, "generate_chart")
    chart_type = resolved.get("chart_type")
    data_points = resolved.get("data_points", [])
    vfs_session_id = resolved.get("vfs_session_id") or state.get("_vfs_session_id", "")
    vfs = get_vfs(vfs_session_id)

    plt.figure(figsize=(6, 4))
    x = [d["label"] for d in data_points]
    y = [d["value"] for d in data_points]

    if chart_type == "bar":
        plt.bar(x, y, color="skyblue")
    elif chart_type == "pie":
        plt.pie(y, labels=x, autopct="%1.1f%%")
    else:
        return _bind_outputs(f"不支持的图表类型: {chart_type}", output_bindings)

    fid = uuid.uuid4().hex[:8]
    filename = f"charts/chart_{fid}.png"
    path = vfs.root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, format="png", dpi=150)
    plt.close()

    return _bind_outputs(str(path), output_bindings)


@tool
async def save_to_vfs(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """将内容保存到 VFS 作为最终产物。"""
    resolved = _resolve_inputs(state, input_bindings, "save_to_vfs")
    filename = resolved.get("filename")
    content = resolved.get("content", "")
    vfs_session_id = resolved.get("vfs_session_id") or state.get("_vfs_session_id", "")
    vfs = get_vfs(vfs_session_id)
    result = vfs.write(filename, content)
    return _bind_outputs(result, output_bindings)


@tool
async def knowledge_search(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """检索知识库文档，根据关键词返回相关文档内容及相似度评分。"""
    resolved = _resolve_inputs(state, input_bindings, "knowledge_search")
    query = resolved.get("query", "") or ""
    top_k = resolved.get("top_k", 5) or 5
    results = _simple_search(str(query), MOCK_DOCS, int(top_k))
    return _bind_outputs(results, output_bindings)


@tool
async def user_input(
    state: dict,
    input_bindings: list[dict],
    output_bindings: list[dict] | None = None,
) -> dict:
    """用户输入节点——透传用户在画布上输入的内容。"""
    resolved = _resolve_inputs(state, input_bindings, "user_input")
    content = resolved.get("content", "")
    return _bind_outputs({"output01": content + "tool01"}, output_bindings)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "query_business_data": query_business_data,
    "check_consistency": check_consistency,
    "generate_chart": generate_chart,
    "save_to_vfs": save_to_vfs,
    "knowledge_search": knowledge_search,
    "user_input": user_input,
}
