"""
Open Canvas 节点函数

包含所有图节点的实现
"""

# 第一批: 基础节点
from .generate_followup import generate_followup
from .reply_to_general_input import reply_to_general_input
from .reflect import reflect_node
from .generate_title import generate_title_node

# 第二批: 工件操作节点
from .update_artifact import update_artifact
from .update_highlighted_text import update_highlighted_text
from .rewrite_artifact_theme import rewrite_artifact_theme
from .rewrite_code_artifact_theme import rewrite_code_artifact_theme

# 第三批: 核心生成节点
from .generate_artifact import generate_artifact
from .rewrite_artifact import rewrite_artifact
from .custom_action import custom_action

# 第四批: 路由节点
from .generate_path import generate_path

__all__ = [
    # 第一批
    "generate_followup",
    "reply_to_general_input",
    "reflect_node",
    "generate_title_node",
    # 第二批
    "update_artifact",
    "update_highlighted_text",
    "rewrite_artifact_theme",
    "rewrite_code_artifact_theme",
    # 第三批
    "generate_artifact",
    "rewrite_artifact",
    "custom_action",
    # 第四批
    "generate_path",
]
