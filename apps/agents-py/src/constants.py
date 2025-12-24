"""
Open Canvas 共享常量定义

与 TypeScript packages/shared/src/constants.ts 保持一致
"""

from typing import Any

# ============================================
# 消息标记常量
# ============================================

OC_SUMMARIZED_MESSAGE_KEY = "__oc_summarized_message"
OC_HIDE_FROM_UI_KEY = "__oc_hide_from_ui"
OC_WEB_SEARCH_RESULTS_MESSAGE_KEY = "__oc_web_search_results_message"

# ============================================
# 命名空间常量
# ============================================

CONTEXT_DOCUMENTS_NAMESPACE = ("context_documents",)

# ============================================
# 摘要触发阈值
# ============================================

# ~ 4 chars per token, max tokens of 75000
# 75000 * 4 = 300000
CHARACTER_MAX = 300000

# ============================================
# 默认输入值 - camelCase (与 TS DEFAULT_INPUTS 对齐)
# ============================================

DEFAULT_INPUTS: dict[str, Any] = {
    "highlightedCode": None,
    "highlightedText": None,
    "next": None,
    "language": None,
    "artifactLength": None,
    "regenerateWithEmojis": None,
    "readingLevel": None,
    "addComments": None,
    "addLogs": None,
    "fixBugs": None,
    "portLanguage": None,
    "customQuickActionId": None,
    "webSearchEnabled": None,
    "webSearchResults": None,
}

# ============================================
# 模型配置
# ============================================

# 不支持温度参数的模型 (推理模型)
# 参考: packages/shared/src/models.ts:696 TEMPERATURE_EXCLUDED_MODELS
TEMPERATURE_EXCLUDED_MODELS = [
    "o3-mini",
    "o4-mini",
    "gpt-5.2",
    "gpt-5.1",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
]

# 思考模型 - 在生成最终响应前执行 CoT 推理
# 参考: packages/shared/src/models.ts:721 THINKING_MODELS
THINKING_MODELS = [
    "accounts/fireworks/models/deepseek-r1",
    "groq/deepseek-r1-distill-llama-70b",
]

# LangChain 用户专属模型
# 当前为空数组，保留扩展能力
# 参考: packages/shared/src/models.ts:692 LANGCHAIN_USER_ONLY_MODELS
LANGCHAIN_USER_ONLY_MODELS: list[str] = []

# ============================================
# 编程语言列表
# ============================================

PROGRAMMING_LANGUAGES = [
    {"language": "typescript", "label": "TypeScript"},
    {"language": "javascript", "label": "JavaScript"},
    {"language": "cpp", "label": "C++"},
    {"language": "java", "label": "Java"},
    {"language": "php", "label": "PHP"},
    {"language": "python", "label": "Python"},
    {"language": "html", "label": "HTML"},
    {"language": "sql", "label": "SQL"},
    {"language": "json", "label": "JSON"},
    {"language": "rust", "label": "Rust"},
    {"language": "xml", "label": "XML"},
    {"language": "clojure", "label": "Clojure"},
    {"language": "csharp", "label": "C#"},
    {"language": "other", "label": "Other"},
]
