import type { AnswerStreamEvent } from "@/schema/conversation/answer-stream.schema";
import type { Citation } from "@/schema/conversation/conversation.schema";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "retrieving" | "streaming" | "complete" | "failed" | "cancelled";
  citations?: Citation[];
  abstained?: boolean;
};

export function applyAnswerEvent(
  message: ChatMessage,
  event: AnswerStreamEvent,
): ChatMessage {
  switch (event.event) {
    case "retrieval_completed":
      return { ...message, status: "streaming" };
    case "answer_delta":
      return {
        ...message,
        content: message.content + event.data.text,
        status: "streaming",
      };
    case "citations":
      return { ...message, citations: event.data.items };
    case "completed":
      return {
        ...message,
        id: event.data.answer_message_id,
        status: "complete",
        abstained: event.data.abstained,
      };
    case "failure":
      return { ...message, status: "failed" };
    case "retrieval_started":
      return message;
  }
}
