"""Seed data – aligned with v3 Node Schema (execution_mode: agent | tool)."""

import json

from sqlalchemy.orm import Session

from app.db.models import Tool, Workflow


def seed(db: Session):
    if db.query(Tool).first():
        return

    # -----------------------------------------------------------------------
    # Tools (metadata only – actual implementations live in engine/tools.py)
    # -----------------------------------------------------------------------
    tools = [
        Tool(
            name="资产数据查询",
            description="根据场景标签查询设备特征值、风险等级及联动逻辑，格式化为 Markdown 表格。",
            component_type="query_business_data",
            category="data_source",
            enabled=True,
            inputs=json.dumps([
                {"name": "scene_id", "type": "string", "required": True, "description": "场景标识"},
                {"name": "min_score", "type": "number", "default": 60, "description": "特征分值下限"},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "device_table_md", "type": "string", "description": "Markdown 设备表"},
                {"name": "raw_json_data", "type": "json", "description": "结构化原始数据"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="一致性校验",
            description="核对方案原文与业务数据一致性，返回 pass/fail + 违规项。",
            component_type="check_consistency",
            category="validator",
            enabled=True,
            inputs=json.dumps([
                {"name": "draft_content", "type": "string", "required": True, "description": "方案文本"},
                {"name": "scene_id", "type": "string", "required": True, "description": "场景标识"},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "validation_result", "type": "json", "description": "{status, violations}"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="图表生成",
            description="绘制柱状图或饼图并存入 VFS。",
            component_type="generate_chart",
            category="executor",
            enabled=True,
            inputs=json.dumps([
                {"name": "chart_type", "type": "string", "required": True, "description": "bar 或 pie"},
                {"name": "data_points", "type": "array", "required": True, "description": "[{label, value}]"},
                {"name": "vfs_session_id", "type": "string", "required": True},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "file_path", "type": "string", "description": "VFS 文件路径"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="VFS 保存",
            description="将内容写入 VFS 作为最终产物。",
            component_type="save_to_vfs",
            category="executor",
            enabled=True,
            inputs=json.dumps([
                {"name": "filename", "type": "string", "required": True},
                {"name": "content", "type": "string", "required": True},
                {"name": "vfs_session_id", "type": "string", "required": True},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "file_path", "type": "string", "description": "VFS 文件路径"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="知识库查询",
            description="根据关键词检索知识库文档，返回相关文档内容及相似度评分。",
            component_type="knowledge_search",
            category="knowledge",
            enabled=True,
            inputs=json.dumps([
                {"name": "query", "type": "string", "required": True, "description": "检索关键词"},
                {"name": "top_k", "type": "number", "default": 5, "description": "返回结果数量上限"},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "results", "type": "json", "description": "检索结果列表 [{id, title, content, score, source}]"},
                {"name": "total", "type": "number", "description": "匹配文档总数"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="用户确认",
            description="HITL 节点——暂停工作流等待用户确认。",
            component_type="human_confirm",
            category="interactor",
            enabled=True,
            inputs=json.dumps([
                {"name": "content", "type": "string", "required": True, "description": "需确认内容"},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "approved", "type": "boolean", "description": "是否确认"},
                {"name": "feedback", "type": "string", "description": "用户反馈"},
            ], ensure_ascii=False),
        ),
        Tool(
            name="用户输入",
            description="工作流起始节点——用户在画布上输入内容，供下游节点引用。",
            component_type="user_input",
            category="interactor",
            enabled=True,
            inputs=json.dumps([
                {"name": "content", "type": "string", "required": True, "description": "用户输入内容"},
            ], ensure_ascii=False),
            outputs=json.dumps([
                {"name": "content", "type": "string", "description": "用户输入内容透传"},
            ], ensure_ascii=False),
        ),
    ]
    db.add_all(tools)

    # -----------------------------------------------------------------------
    # Demo workflow (v3 schema)
    # -----------------------------------------------------------------------
    demo_workflow = Workflow(
        name="标准方案生成流程",
        description="检索 → 写作 → 校验，校验失败回退重写（最多3次）。",
        is_published=True,
        nodes=json.dumps([
            {
                "id": "research",
                "execution_mode": "agent",
                "name": "数据检索",
                "description": "查询场景设备特征与风险数据",
                "category": "data_source",
                "icon": "search",
                "version": "1.0.0",
                "agent_config": {
                    "system_prompt": "你是数据检索专家。请调用 query_business_data 查询给定场景的设备特征与风险数据，将结果整理后返回。",
                    "tool_names": ["query_business_data"],
                    "llm_params": {"temperature": 0},
                },
                "output_bindings": [
                    {"output_name": "final_text", "state_key": "data_query_result"},
                ],
                "requires_approval": False,
            },
            {
                "id": "writing",
                "execution_mode": "agent",
                "name": "方案编写",
                "description": "基于检索数据生成方案全文",
                "category": "executor",
                "icon": "pen",
                "version": "1.0.0",
                "agent_config": {
                    "system_prompt": "你是方案编写专家。基于提供的业务数据，生成完整的防范方案，如有需要调用 generate_chart 生成图表，调用 save_to_vfs 保存成品。返回方案全文。",
                    "tool_names": ["generate_chart", "save_to_vfs"],
                    "llm_params": {"temperature": 0.7},
                },
                "output_bindings": [
                    {"output_name": "final_text", "state_key": "draft_content"},
                ],
                "requires_approval": False,
            },
            {
                "id": "validation",
                "execution_mode": "tool",
                "name": "一致性校验",
                "description": "核对方案与业务数据一致性",
                "category": "validator",
                "icon": "shield-check",
                "version": "1.0.0",
                "tool_config": {
                    "tool_name": "check_consistency",
                    "input_bindings": [
                        {"name": "draft_content", "bind": {"type": "state", "state_key": "draft_content"}, "required": True},
                        {"name": "scene_id", "bind": {"type": "state", "state_key": "business_context.scene_id"}, "required": True},
                    ],
                    "output_bindings": [
                        {"output_name": "validation_result", "state_key": "consistency_report"},
                    ],
                },
                "requires_approval": False,
            },
        ], ensure_ascii=False),
        edges=json.dumps([
            {"id": "e_start_research", "source": "__start__", "target": "research"},
            {"id": "e_research_writing", "source": "research", "target": "writing"},
            {"id": "e_writing_validation", "source": "writing", "target": "validation"},
            {
                "id": "e_validation_writing",
                "source": "validation",
                "target": "writing",
                "condition": {"field": "consistency_report.status", "operator": "eq", "value": "fail"},
                "max_retries": 3,
            },
            {
                "id": "e_validation_end",
                "source": "validation",
                "target": "__end__",
                "condition": {"field": "consistency_report.status", "operator": "eq", "value": "pass"},
            },
        ], ensure_ascii=False),
    )
    db.add(demo_workflow)
    db.commit()
