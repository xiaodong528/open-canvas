import { type Example, Run } from "langsmith";
import { evaluate, EvaluationResult } from "langsmith/evaluation";
import {
  createEvalsClient,
  DEFAULT_MODEL_CONFIG,
  getArtifactContent,
  PyArtifact,
} from "./utils";
import "dotenv/config";

const client = createEvalsClient();

const runGraph = async (
  input: Record<string, any>
): Promise<Record<string, any>> => {
  const thread = await client.threads.create();

  try {
    // 使用 SDK stream 调用
    // 重要: 必须传入 customModelName，否则 Python 端会抛错
    const stream = client.runs.stream(thread.thread_id, "agent", {
      input,
      streamMode: "values",
      config: {
        configurable: {
          customModelName: DEFAULT_MODEL_CONFIG.customModelName,
        },
      },
    });

    let finalState: Record<string, any> | null = null;
    for await (const chunk of stream) {
      if (chunk.event === "values") {
        finalState = chunk.data;
      }
    }

    return finalState ?? {};
  } finally {
    // Clean up
    try {
      await client.threads.delete(thread.thread_id);
    } catch {
      // Ignore cleanup errors
    }
  }
};

const evaluateHighlights = (run: Run, example?: Example): EvaluationResult => {
  if (!example) {
    throw new Error("No example provided");
  }
  if (!example.outputs) {
    throw new Error("No example outputs provided");
  }
  if (!run.outputs) {
    throw new Error("No run outputs provided");
  }

  const { expectedGeneration } = example.outputs;
  const { artifact, highlightedText, highlighted } = example.inputs;

  // 兼容两种输入格式：highlightedText (Python) 或 highlighted (旧 TS)
  const highlightInfo = highlightedText || highlighted;

  // Python 端 artifact 结构: artifact.contents[currentIndex]
  const pyArtifact = artifact as PyArtifact;
  const inputContent = getArtifactContent(pyArtifact);
  const originalContent =
    inputContent?.fullMarkdown || inputContent?.code || "";

  const expectedGenerationStart = originalContent.slice(
    0,
    highlightInfo.startCharIndex
  );
  const expectedGenerationEnd = originalContent.slice(
    highlightInfo.endCharIndex
  );
  const fullExpectedArtifact = `${expectedGenerationStart}${expectedGeneration}${expectedGenerationEnd}`;

  // Python 端输出结构
  const outputArtifact = run.outputs.artifact as PyArtifact;
  const outputContent = getArtifactContent(outputArtifact);
  const generatedArtifact =
    outputContent?.fullMarkdown || outputContent?.code || "";

  if (generatedArtifact !== fullExpectedArtifact) {
    return {
      key: "correct_generation",
      score: false,
    };
  }
  return {
    key: "correct_generation",
    score: true,
  };
};

async function runHighlightEval() {
  const datasetName = "open-canvas-deterministic-highlights";
  await evaluate(runGraph, {
    data: datasetName,
    evaluators: [evaluateHighlights],
    experimentPrefix: "Highlight generation",
  });
}

runHighlightEval().catch(console.error);
