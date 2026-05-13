import type { ChatMessage, CPNAResponse } from "@/lib/types";
import { TherapyCard } from "@/components/response-cards/TherapyCard";
import { RecommendationCard } from "@/components/response-cards/RecommendationCard";
import { ComparisonCard } from "@/components/response-cards/ComparisonCard";
import { GeneralCard } from "@/components/response-cards/GeneralCard";

interface Props {
  message: ChatMessage;
}

function ResponseCard({ response }: { response: CPNAResponse }) {
  switch (response.query_type) {
    case "therapy":
      return <TherapyCard data={response} />;
    case "recommendation":
      return <RecommendationCard data={response} />;
    case "comparison":
      return <ComparisonCard data={response} />;
    case "general":
      return <GeneralCard data={response} />;
  }
}

export function MessageBubble({ message }: Props) {
  if (message.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
        <div
          style={{
            background: "#E8F5F3",
            color: "#1C1C1A",
            borderRadius: "16px 16px 4px 16px",
            padding: "10px 16px",
            maxWidth: "72%",
            fontSize: "0.9rem",
            fontFamily: "var(--font-body)",
            lineHeight: 1.5,
          }}
        >
          {typeof message.content === "string" ? message.content : null}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "0.75rem" }}>
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E5E3DF",
          borderRadius: "4px 16px 16px 16px",
          padding: "14px 18px",
          maxWidth: "88%",
          boxShadow: "0 1px 4px rgba(0,0,0,0.07)",
          fontFamily: "var(--font-body)",
          lineHeight: 1.55,
          fontSize: "0.9rem",
          color: "#1C1C1A",
        }}
      >
        {typeof message.content === "string" ? (
          <p style={{ margin: 0 }}>{message.content}</p>
        ) : (
          <ResponseCard response={message.content} />
        )}
      </div>
    </div>
  );
}
