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
    case "therapy":      return <TherapyCard data={response} />;
    case "recommendation": return <RecommendationCard data={response} />;
    case "comparison":   return <ComparisonCard data={response} />;
    case "general":      return <GeneralCard data={response} />;
  }
}

export function MessageBubble({ message }: Props) {
  if (message.role === "user") {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "1rem" }}>
        <div style={{
          background: "linear-gradient(135deg, #0F2040, #0A1830)",
          color: "#E8EDF5",
          borderRadius: "16px 16px 4px 16px",
          padding: "10px 16px",
          maxWidth: "72%",
          fontSize: "0.9rem",
          fontFamily: "var(--font-body)",
          lineHeight: 1.5,
          border: "1px solid rgba(0,255,148,0.15)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.3)",
        }}>
          {typeof message.content === "string" ? message.content : null}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1rem" }}>
      {/* Assistant avatar dot */}
      <div style={{
        width: 28, height: 28, borderRadius: "8px", flexShrink: 0,
        background: "rgba(0,255,148,0.08)",
        border: "1px solid rgba(0,255,148,0.2)",
        display: "flex", alignItems: "center", justifyContent: "center",
        marginRight: "0.5rem", marginTop: "2px",
      }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#00FF94", boxShadow: "0 0 6px #00FF94" }}/>
      </div>

      <div style={{
        background: "rgba(15,21,37,0.95)",
        border: "1px solid rgba(30,45,74,0.9)",
        borderRadius: "4px 16px 16px 16px",
        padding: "14px 18px",
        maxWidth: "calc(88% - 36px)",
        boxShadow: "0 2px 16px rgba(0,0,0,0.4)",
        fontFamily: "var(--font-body)",
        lineHeight: 1.55,
        fontSize: "0.9rem",
        color: "#E8EDF5",
      }}>
        {typeof message.content === "string" ? (
          <p style={{ margin: 0 }}>{message.content}</p>
        ) : (
          <ResponseCard response={message.content} />
        )}
      </div>
    </div>
  );
}
