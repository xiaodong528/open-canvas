import { Client } from "@langchain/langgraph-sdk";

/**
 * Python LangGraph Server URL
 * 直连 Python 后端，不经过 Next.js 代理
 */
export const PYTHON_BACKEND_URL =
  process.env.LANGGRAPH_API_URL ?? "http://localhost:54367";

/**
 * 创建 evals 专用的 LangGraph SDK 客户端
 * 直连 Python LangGraph Server，不经过 Next.js 代理
 */
export const createEvalsClient = () => {
  return new Client({ apiUrl: PYTHON_BACKEND_URL });
};

/**
 * 默认模型配置
 * 重要: Python 端 get_model_config() 必须有 customModelName，否则会抛错
 * 参考: apps/agents-py/src/utils.py:220-221
 */
export const DEFAULT_MODEL_CONFIG = {
  customModelName: "gpt-4o-mini",
};

/**
 * Artifact 内容结构 (Python 端)
 */
export interface PyArtifactContent {
  index: number;
  type: "code" | "text";
  title: string;
  code?: string;
  language?: string;
  fullMarkdown?: string;
}

/**
 * Artifact 结构 (Python 端)
 * 与 TypeScript 的主要差异:
 * - TS: artifacts[0].content
 * - Python: artifact.contents[currentIndex].fullMarkdown
 */
export interface PyArtifact {
  currentIndex: number;
  contents: PyArtifactContent[];
}

/**
 * 获取 artifact 的当前内容
 */
export const getArtifactContent = (
  artifact: PyArtifact | undefined
): PyArtifactContent | undefined => {
  if (!artifact || !artifact.contents || artifact.contents.length === 0) {
    return undefined;
  }
  return artifact.contents[artifact.currentIndex] ?? artifact.contents[0];
};
