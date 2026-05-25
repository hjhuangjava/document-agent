"""Tool registry – all @tool functions live here. No dynamic code execution."""

import uuid

import matplotlib
matplotlib.use("Agg")  # non-interactive backend for servers
import matplotlib.pyplot as plt
from langchain_core.tools import tool

from app.engine.vfs import VirtualFileSystem
from app.api.knowledge import _simple_search, MOCK_DOCS

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
def query_business_data(scene_id: str, min_score: int = 60) -> str:
    """查询资产特征库，返回设备特征、风险等级及联动逻辑。
    结果格式化为 Markdown 表格。scene_id 为场景标识，min_score 为特征分值过滤下限。"""
    # TODO: replace with real DB / Neo4j query
    return (
        "| 设备名称 | 特征分值 | 风险等级 |\n"
        "|----------|----------|----------|\n"
        f"| 示例设备A | 85 | 高 |\n"
        f"| 示例设备B | {min_score} | 中 |\n"
    )


@tool
def check_consistency(draft_content: str, scene_id: str) -> dict:
    """核对方案原文与业务数据的一致性。
    draft_content 是方案文本，scene_id 用于查回原始数据做交叉比对。
    返回 {status: pass/fail, violations: [...]}。"""
    # TODO: replace with real cross-check logic
    return {"status": "pass", "violations": []}


@tool
def generate_chart(chart_type: str, data_points: list[dict], vfs_session_id: str) -> str:
    """绘制图表并存入 VFS。chart_type 可选 'bar'/'pie'，
    data_points 格式为 [{label, value}, ...]。返回 VFS 文件路径。"""
    vfs = get_vfs(vfs_session_id)

    plt.figure(figsize=(6, 4))
    x = [d["label"] for d in data_points]
    y = [d["value"] for d in data_points]

    if chart_type == "bar":
        plt.bar(x, y, color="skyblue")
    elif chart_type == "pie":
        plt.pie(y, labels=x, autopct="%1.1f%%")
    else:
        return f"不支持的图表类型: {chart_type}"

    fid = uuid.uuid4().hex[:8]
    filename = f"charts/chart_{fid}.png"
    path = vfs.root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, format="png", dpi=150)
    plt.close()

    return str(path)


@tool
def save_to_vfs(filename: str, content: str, vfs_session_id: str) -> str:
    """将内容保存到 VFS 作为最终产物（完整文档、图表等）。"""
    vfs = get_vfs(vfs_session_id)
    return vfs.write(filename, content)


@tool
def knowledge_search(query: str, top_k: int = 5) -> dict:
    """检索知识库文档，根据关键词返回相关文档内容及相似度评分。
    query 为检索关键词，top_k 为返回结果数量上限。
    返回 {results: [{id, title, content, score, source, category}], total: int}。"""
    results = _simple_search(query, MOCK_DOCS, top_k)
    return {"results": results, "total": len(results)}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, callable] = {
    "query_business_data": query_business_data,
    "check_consistency": check_consistency,
    "generate_chart": generate_chart,
    "save_to_vfs": save_to_vfs,
    "knowledge_search": knowledge_search,
}
