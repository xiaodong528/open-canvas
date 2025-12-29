import { expect } from "vitest";
import * as ls from "langsmith/vitest";
import { z } from "zod";
import { ChatOpenAI } from "@langchain/openai";
import {
  createEvalsClient,
  DEFAULT_MODEL_CONFIG,
  getArtifactContent,
} from "./utils";
import { QUERY_ROUTING_DATA } from "./data/query_routing.js";
import { CODEGEN_DATA } from "./data/codegen.js";

const client = createEvalsClient();

ls.describe("query routing", () => {
  ls.test(
    "routes followups with questions to update artifact",
    {
      inputs: QUERY_ROUTING_DATA.inputs,
      referenceOutputs: QUERY_ROUTING_DATA.referenceOutputs,
    },
    async ({ inputs, referenceOutputs }) => {
      const thread = await client.threads.create();

      try {
        // 使用 streamMode: "events" 捕获 generatePath 节点输出
        // 重要: cleanState 节点会清空 next 为 None，所以必须捕获中间输出
        const stream = client.runs.stream(thread.thread_id, "agent", {
          input: inputs,
          streamMode: "events",
          config: {
            configurable: {
              customModelName: DEFAULT_MODEL_CONFIG.customModelName,
            },
          },
        });

        let capturedNext: string | null = null;
        for await (const chunk of stream) {
          // 捕获 generatePath 节点的输出
          // 使用类型断言因为 SDK 类型定义不完整
          const event = chunk as { event: string; name?: string; data?: any };
          if (event.event === "on_chain_end" && event.name === "generatePath") {
            capturedNext = event.data?.output?.next ?? null;
            break;
          }
        }

        ls.logOutputs({ next: capturedNext });
        expect(capturedNext).toEqual(referenceOutputs.next);
      } finally {
        // Clean up
        try {
          await client.threads.delete(thread.thread_id);
        } catch {
          // Ignore cleanup errors
        }
      }
    }
  );
});

const qualityEvaluator = async (params: {
  inputs: string;
  outputs: string;
}) => {
  const judge = new ChatOpenAI({ model: "gpt-4o" }).withStructuredOutput(
    z.object({
      justification: z
        .string()
        .describe("reasoning for why you are assigning a given quality score"),
      quality_score: z
        .number()
        .describe(
          "quality score for how well the generated code answers the query."
        ),
    }),
    {
      name: "judge",
    }
  );
  const EVAL_PROMPT = [
    `Given the following user query and generated code, judge whether the`,
    `code satisfies the user's query. Return a quality score between 1 and 10,`,
    `where a 1 would be completely irrelevant to the user's input, and 10 would be a perfectly accurate code sample.`,
    `A 5 would be a code sample that is partially on target, but is missing some aspect of a user's request.`,
    `Justify your answer.\n`,
    `<query>\n${params.inputs}\n</query>\n`,
    `<generated_code>\n${params.outputs}\n</generated_code>`,
  ].join(" ");
  const res = await judge.invoke(EVAL_PROMPT);
  return {
    key: "quality",
    score: res.quality_score,
    comment: res.justification,
  };
};

ls.describe("codegen", () => {
  ls.test(
    "generate code with an LLM agent when asked",
    {
      inputs: CODEGEN_DATA.inputs,
      referenceOutputs: {},
    },
    async ({ inputs }) => {
      const thread = await client.threads.create();

      try {
        // 使用 streamMode: "events" 捕获 generateArtifact 节点输出
        const stream = client.runs.stream(thread.thread_id, "agent", {
          input: inputs,
          streamMode: "events",
          config: {
            configurable: {
              customModelName: DEFAULT_MODEL_CONFIG.customModelName,
            },
          },
        });

        let artifactOutput: any = null;
        for await (const chunk of stream) {
          // 捕获 generateArtifact 节点的输出
          // 使用类型断言因为 SDK 类型定义不完整
          const event = chunk as { event: string; name?: string; data?: any };
          if (
            event.event === "on_chain_end" &&
            event.name === "generateArtifact"
          ) {
            artifactOutput = event.data?.output?.artifact;
            break;
          }
        }

        ls.logOutputs({ artifact: artifactOutput });

        // Python 端 artifact 结构: artifact.contents[0].code
        const content = getArtifactContent(artifactOutput);
        const generatedCode = content?.code;
        expect(generatedCode).toBeDefined();

        const wrappedEvaluator = ls.wrapEvaluator(qualityEvaluator);
        await wrappedEvaluator({
          inputs: inputs.messages[0].content,
          outputs: generatedCode!,
        });
      } finally {
        // Clean up
        try {
          await client.threads.delete(thread.thread_id);
        } catch {
          // Ignore cleanup errors
        }
      }
    }
  );
});
