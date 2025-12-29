import { Client, Feedback } from "langsmith";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { runId, feedbackKey, score, comment } = body;

    if (!runId || !feedbackKey) {
      return NextResponse.json(
        { error: "`runId` and `feedbackKey` are required." },
        { status: 400 }
      );
    }

    if (!process.env.LANGSMITH_API_KEY) {
      return NextResponse.json(
        { error: "LangSmith API key not configured" },
        { status: 500 }
      );
    }

    const lsClient = new Client({
      apiKey: process.env.LANGSMITH_API_KEY,
      apiUrl: process.env.LANGSMITH_ENDPOINT,
    });

    const feedback = await lsClient.createFeedback(runId, feedbackKey, {
      score,
      comment,
    });

    return NextResponse.json(
      { success: true, feedback: feedback },
      { status: 200 }
    );
  } catch (error) {
    console.error("Failed to process feedback request:", error);

    return NextResponse.json(
      { error: "Failed to submit feedback." },
      { status: 500 }
    );
  }
}

export async function GET(req: NextRequest) {
  try {
    const searchParams = req.nextUrl.searchParams;
    const runId = searchParams.get("runId");
    const feedbackKey = searchParams.get("feedbackKey");

    if (!runId || !feedbackKey) {
      return new NextResponse(
        JSON.stringify({
          error: "`runId` and `feedbackKey` are required.",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    if (!process.env.LANGSMITH_API_KEY) {
      return new NextResponse(
        JSON.stringify({ error: "LangSmith API key not configured" }),
        { status: 500, headers: { "Content-Type": "application/json" } }
      );
    }

    const lsClient = new Client({
      apiKey: process.env.LANGSMITH_API_KEY,
      apiUrl: process.env.LANGSMITH_ENDPOINT,
    });

    const runFeedback: Feedback[] = [];

    const run_feedback = await lsClient.listFeedback({
      runIds: [runId],
      feedbackKeys: [feedbackKey],
    });

    for await (const feedback of run_feedback) {
      runFeedback.push(feedback);
    }

    return new NextResponse(
      JSON.stringify({
        feedback: runFeedback,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Failed to fetch feedback:", error);
    return NextResponse.json(
      { error: "Failed to fetch feedback." },
      { status: 500 }
    );
  }
}
