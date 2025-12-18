"""
Open Canvas 共享类型定义

重要: 所有字段名必须与 TypeScript 版本保持一致 (camelCase)
LangGraph Server 不会自动转换 snake_case ↔ camelCase
"""

from typing import Any, Literal, Optional, Union

from typing_extensions import TypedDict


# ============================================
# 语言和选项类型
# ============================================

LanguageOptions = Literal["english", "mandarin", "spanish", "french", "hindi"]

ProgrammingLanguageOptions = Literal[
    "typescript",
    "javascript",
    "cpp",
    "java",
    "php",
    "python",
    "html",
    "sql",
    "json",
    "rust",
    "xml",
    "clojure",
    "csharp",
    "other",
]

ArtifactLengthOptions = Literal["shortest", "short", "long", "longest"]

ReadingLevelOptions = Literal["pirate", "child", "teenager", "college", "phd"]

ArtifactType = Literal["code", "text"]


# ============================================
# 高亮类型 - camelCase 字段名
# ============================================


class CodeHighlight(TypedDict):
    """代码高亮区域"""

    startCharIndex: int
    endCharIndex: int


class TextHighlight(TypedDict):
    """文本高亮区域"""

    fullMarkdown: str
    markdownBlock: str
    selectedText: str


# ============================================
# 工件类型 - camelCase 字段名
# ============================================


class ArtifactMarkdownV3(TypedDict):
    """Markdown 文档版本"""

    index: int
    type: Literal["text"]
    title: str
    fullMarkdown: str


class ArtifactCodeV3(TypedDict, total=False):
    """代码文档版本"""

    index: int
    type: Literal["code"]
    title: str
    language: ProgrammingLanguageOptions
    code: str
    isValidReact: Optional[bool]


# 使用必需字段定义
class ArtifactCodeV3Required(TypedDict):
    """代码文档版本 - 必需字段"""

    index: int
    type: Literal["code"]
    title: str
    language: ProgrammingLanguageOptions
    code: str


class ArtifactV3(TypedDict):
    """文档 V3 - 支持版本控制"""

    currentIndex: int
    contents: list[Union[ArtifactMarkdownV3, ArtifactCodeV3]]


# ============================================
# 模型配置类型
# ============================================


class AzureConfig(TypedDict, total=False):
    """Azure OpenAI 配置"""

    azureOpenAIApiKey: str
    azureOpenAIApiInstanceName: str
    azureOpenAIApiDeploymentName: str
    azureOpenAIApiVersion: str
    azureOpenAIBasePath: Optional[str]


class TemperatureRange(TypedDict):
    """温度范围配置"""

    min: float
    max: float
    default: float
    current: float


class MaxTokensRange(TypedDict):
    """最大 Token 范围配置"""

    min: int
    max: int
    default: int
    current: int


class CustomModelConfig(TypedDict, total=False):
    """自定义模型配置"""

    provider: str
    temperatureRange: TemperatureRange
    maxTokens: MaxTokensRange
    azureConfig: Optional[AzureConfig]


class ModelConfigurationParams(TypedDict, total=False):
    """模型配置参数"""

    name: str
    label: str
    modelName: Optional[str]
    config: CustomModelConfig
    isNew: bool


# ============================================
# 快捷操作类型
# ============================================


class CustomQuickAction(TypedDict):
    """自定义快捷操作"""

    id: str
    title: str
    prompt: str
    includeReflections: bool
    includePrefix: bool
    includeRecentHistory: bool


# ============================================
# 反思/记忆类型
# ============================================


class Reflections(TypedDict):
    """用户反思和记忆"""

    styleRules: list[str]
    content: list[str]


# ============================================
# 上下文文档类型
# ============================================


class ContextDocument(TypedDict, total=False):
    """上下文文档"""

    name: str
    type: str
    data: str
    metadata: Optional[dict[str, Any]]


# ============================================
# 搜索结果类型 (Exa) - camelCase 与前端一致
# ============================================


class SearchResult(TypedDict):
    """Exa 搜索结果 - 保持 camelCase 与 TS 完全一致"""

    id: str
    url: str
    title: str
    author: str
    publishedDate: str
    pageContent: str


# ============================================
# 图输入类型
# ============================================


class GraphInput(TypedDict, total=False):
    """图输入类型 - 前端发送的数据"""

    messages: Optional[list[dict[str, Any]]]

    highlightedCode: Optional[CodeHighlight]
    highlightedText: Optional[TextHighlight]

    artifact: Optional[ArtifactV3]

    next: Optional[str]

    language: Optional[LanguageOptions]
    artifactLength: Optional[ArtifactLengthOptions]
    regenerateWithEmojis: Optional[bool]
    readingLevel: Optional[ReadingLevelOptions]

    addComments: Optional[bool]
    addLogs: Optional[bool]
    portLanguage: Optional[ProgrammingLanguageOptions]
    fixBugs: Optional[bool]
    customQuickActionId: Optional[str]

    webSearchEnabled: Optional[bool]
    webSearchResults: Optional[list[SearchResult]]


# ============================================
# 工具响应类型
# ============================================


class ArtifactToolResponse(TypedDict, total=False):
    """工件工具响应"""

    artifact: Optional[str]
    title: Optional[str]
    language: Optional[str]
    type: Optional[str]
    isValidReact: Optional[bool]


class RewriteArtifactMetaToolResponseText(TypedDict, total=False):
    """重写工件元数据响应 - 文本类型"""

    type: Literal["text"]
    title: Optional[str]
    language: ProgrammingLanguageOptions


class RewriteArtifactMetaToolResponseCode(TypedDict, total=False):
    """重写工件元数据响应 - 代码类型"""

    type: Literal["code"]
    title: str
    language: ProgrammingLanguageOptions
    isValidReact: Optional[bool]


RewriteArtifactMetaToolResponse = Union[
    RewriteArtifactMetaToolResponseText, RewriteArtifactMetaToolResponseCode
]
