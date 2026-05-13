export function TypingIndicator() {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: "1rem", alignItems: "flex-start" }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, borderRadius: "8px", flexShrink: 0,
        background: "rgba(0,255,148,0.08)",
        border: "1px solid rgba(0,255,148,0.2)",
        display: "flex", alignItems: "center", justifyContent: "center",
        marginRight: "0.5rem",
      }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#00FF94", boxShadow: "0 0 6px #00FF94" }}/>
      </div>

      <div style={{
        background: "rgba(15,21,37,0.95)",
        border: "1px solid rgba(30,45,74,0.9)",
        borderRadius: "4px 16px 16px 16px",
        padding: "14px 20px",
        boxShadow: "0 2px 16px rgba(0,0,0,0.4)",
        display: "flex", gap: "6px", alignItems: "center",
      }}>
        {[0, 1, 2].map((i) => (
          <span key={i} style={{
            display: "inline-block", width: "7px", height: "7px",
            borderRadius: "50%", background: "#00FF94",
            animation: `bounce-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}/>
        ))}
        <style>{`
          @keyframes bounce-dot {
            0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
            40% { transform: translateY(-6px); opacity: 1; box-shadow: 0 0 8px #00FF94; }
          }
        `}</style>
      </div>
    </div>
  );
}
