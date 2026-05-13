"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

/* ─── NutriIntel Logo SVG ─── */
function NutriIntelLogo({ size = 40 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="40" height="40" rx="10" fill="#0F1525" stroke="#00FF94" strokeWidth="1.5"/>
      {/* Hexagon outline */}
      <path d="M20 6L32 13V27L20 34L8 27V13L20 6Z" stroke="#00FF94" strokeWidth="1.2" fill="none" opacity="0.4"/>
      {/* Inner cross/molecule node */}
      <circle cx="20" cy="20" r="3.5" fill="#00FF94"/>
      <line x1="20" y1="10" x2="20" y2="16.5" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="20" y1="23.5" x2="20" y2="30" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="11" y1="15" x2="16.7" y2="18.3" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="23.3" y1="21.7" x2="29" y2="25" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="29" y1="15" x2="23.3" y2="18.3" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      <line x1="16.7" y1="21.7" x2="11" y2="25" stroke="#00FF94" strokeWidth="1.2" opacity="0.8"/>
      {/* Node dots */}
      <circle cx="20" cy="10" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="20" cy="30" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="11" cy="15" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="29" cy="15" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="11" cy="25" r="1.5" fill="#00FF94" opacity="0.6"/>
      <circle cx="29" cy="25" r="1.5" fill="#00FF94" opacity="0.6"/>
    </svg>
  );
}

/* ─── Animated grid background ─── */
function GridBackground() {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden",
    }}>
      {/* Animated grid */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: `linear-gradient(rgba(0,255,148,0.04) 1px, transparent 1px),
                          linear-gradient(90deg, rgba(0,255,148,0.04) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
        animation: "grid-flow 8s linear infinite",
      }}/>
      {/* Radial glow top */}
      <div style={{
        position: "absolute", top: "-20%", left: "50%", transform: "translateX(-50%)",
        width: "800px", height: "600px",
        background: "radial-gradient(ellipse, rgba(0,255,148,0.08) 0%, transparent 70%)",
      }}/>
      {/* Purple glow bottom-right */}
      <div style={{
        position: "absolute", bottom: "-10%", right: "-10%",
        width: "500px", height: "500px",
        background: "radial-gradient(ellipse, rgba(124,77,255,0.06) 0%, transparent 70%)",
      }}/>
      {/* Scanline */}
      <div style={{
        position: "absolute", left: 0, right: 0, height: "2px",
        background: "linear-gradient(90deg, transparent, rgba(0,255,148,0.15), transparent)",
        animation: "scanline 6s linear infinite",
      }}/>
    </div>
  );
}

/* ─── Animated molecule/network SVG illustration ─── */
function MoleculeIllustration() {
  return (
    <div style={{ position: "relative", width: "100%", maxWidth: 520, margin: "0 auto", animation: "float 4s ease-in-out infinite" }}>
      <svg viewBox="0 0 520 420" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: "100%", filter: "drop-shadow(0 0 30px rgba(0,255,148,0.2))" }}>
        {/* Outer ring */}
        <circle cx="260" cy="210" r="160" stroke="rgba(0,255,148,0.08)" strokeWidth="1" strokeDasharray="6 4"/>
        <circle cx="260" cy="210" r="120" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>

        {/* Network connections */}
        <line x1="260" y1="210" x2="150" y2="100" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        <line x1="260" y1="210" x2="370" y2="100" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        <line x1="260" y1="210" x2="400" y2="240" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        <line x1="260" y1="210" x2="310" y2="340" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        <line x1="260" y1="210" x2="140" y2="340" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        <line x1="260" y1="210" x2="120" y2="240" stroke="rgba(0,255,148,0.3)" strokeWidth="1"/>
        {/* Cross-connections */}
        <line x1="150" y1="100" x2="370" y2="100" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>
        <line x1="400" y1="240" x2="310" y2="340" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>
        <line x1="140" y1="340" x2="120" y2="240" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>
        <line x1="150" y1="100" x2="120" y2="240" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>
        <line x1="370" y1="100" x2="400" y2="240" stroke="rgba(0,255,148,0.12)" strokeWidth="1"/>

        {/* Central node */}
        <circle cx="260" cy="210" r="22" fill="#0F1525" stroke="#00FF94" strokeWidth="2"/>
        <circle cx="260" cy="210" r="14" fill="#00FF94" opacity="0.2"/>
        <circle cx="260" cy="210" r="7" fill="#00FF94"/>

        {/* Outer nodes */}
        <circle cx="150" cy="100" r="14" fill="#0F1525" stroke="#00FF94" strokeWidth="1.5"/>
        <circle cx="150" cy="100" r="7" fill="#00FF94" opacity="0.5"/>
        <circle cx="370" cy="100" r="14" fill="#0F1525" stroke="#7C4DFF" strokeWidth="1.5"/>
        <circle cx="370" cy="100" r="7" fill="#7C4DFF" opacity="0.5"/>
        <circle cx="400" cy="240" r="14" fill="#0F1525" stroke="#00FF94" strokeWidth="1.5"/>
        <circle cx="400" cy="240" r="7" fill="#00FF94" opacity="0.5"/>
        <circle cx="310" cy="340" r="14" fill="#0F1525" stroke="#FFB547" strokeWidth="1.5"/>
        <circle cx="310" cy="340" r="7" fill="#FFB547" opacity="0.5"/>
        <circle cx="140" cy="340" r="14" fill="#0F1525" stroke="#7C4DFF" strokeWidth="1.5"/>
        <circle cx="140" cy="340" r="7" fill="#7C4DFF" opacity="0.5"/>
        <circle cx="120" cy="240" r="14" fill="#0F1525" stroke="#00FF94" strokeWidth="1.5"/>
        <circle cx="120" cy="240" r="7" fill="#00FF94" opacity="0.5"/>

        {/* Labels */}
        <text x="122" y="84" fill="rgba(0,255,148,0.7)" fontSize="10" fontFamily="monospace">DRI</text>
        <text x="372" y="84" fill="rgba(124,77,255,0.8)" fontSize="10" fontFamily="monospace">FCT</text>
        <text x="408" y="236" fill="rgba(0,255,148,0.7)" fontSize="10" fontFamily="monospace">BM25</text>
        <text x="312" y="358" fill="rgba(255,181,71,0.8)" fontSize="10" fontFamily="monospace">RAG</text>
        <text x="96" y="358" fill="rgba(124,77,255,0.8)" fontSize="10" fontFamily="monospace">PKU</text>
        <text x="80" y="236" fill="rgba(0,255,148,0.7)" fontSize="10" fontFamily="monospace">Embed</text>

        {/* Data flow pulses (animated via CSS is not doable inline, use opacity trick) */}
        <circle cx="260" cy="210" r="30" stroke="#00FF94" strokeWidth="1" opacity="0.2" strokeDasharray="3 6"/>
        <circle cx="260" cy="210" r="45" stroke="#00FF94" strokeWidth="1" opacity="0.1" strokeDasharray="3 9"/>
      </svg>
    </div>
  );
}

/* ─── Stat counter ─── */
function StatCard({ value, label, delay }: { value: string; label: string; delay: number }) {
  return (
    <div style={{
      animation: `fadeUp 0.6s ease ${delay}ms both`,
      textAlign: "center",
      padding: "1.5rem",
      background: "rgba(15,21,37,0.8)",
      border: "1px solid rgba(0,255,148,0.15)",
      borderRadius: "12px",
      backdropFilter: "blur(10px)",
    }}>
      <div style={{
        fontSize: "2.2rem", fontWeight: 800, color: "#00FF94",
        fontFamily: "var(--font-mono)",
        textShadow: "0 0 20px rgba(0,255,148,0.4)",
      }}>{value}</div>
      <div style={{ color: "#8B9BB4", fontSize: "0.8rem", marginTop: "0.3rem", letterSpacing: "0.08em", textTransform: "uppercase" }}>{label}</div>
    </div>
  );
}

/* ─── Feature card ─── */
function FeatureCard({ icon, title, body, delay, accent = "#00FF94" }: {
  icon: string; title: string; body: string; delay: number; accent?: string;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        animation: `fadeUp 0.6s ease ${delay}ms both`,
        padding: "1.75rem",
        background: hovered ? "rgba(15,21,37,0.95)" : "rgba(15,21,37,0.7)",
        border: `1px solid ${hovered ? accent : "rgba(30,45,74,0.8)"}`,
        borderRadius: "16px",
        backdropFilter: "blur(12px)",
        transition: "all 0.25s ease",
        transform: hovered ? "translateY(-4px)" : "none",
        boxShadow: hovered ? `0 8px 32px ${accent}22` : "none",
        cursor: "default",
      }}
    >
      <div style={{ fontSize: "1.8rem", marginBottom: "0.75rem" }}>{icon}</div>
      <h3 style={{ color: "#E8EDF5", fontWeight: 700, marginBottom: "0.5rem", fontSize: "1rem" }}>{title}</h3>
      <p style={{ color: "#8B9BB4", fontSize: "0.875rem", lineHeight: 1.6 }}>{body}</p>
    </div>
  );
}

/* ─── Source pill ─── */
function SourcePill({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      display: "inline-block",
      padding: "0.35rem 0.85rem",
      borderRadius: "999px",
      border: `1px solid ${color}44`,
      background: `${color}0F`,
      color: color,
      fontSize: "0.78rem",
      fontFamily: "var(--font-mono)",
      letterSpacing: "0.04em",
      margin: "0.25rem",
    }}>{label}</span>
  );
}

/* ─── Navbar ─── */
function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <nav style={{
      position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "0.9rem 2rem",
      background: scrolled ? "rgba(10,14,26,0.95)" : "transparent",
      backdropFilter: scrolled ? "blur(16px)" : "none",
      borderBottom: scrolled ? "1px solid rgba(0,255,148,0.08)" : "none",
      transition: "all 0.3s ease",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
        <NutriIntelLogo size={34} />
        <span style={{
          fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "1rem",
          color: "#E8EDF5", letterSpacing: "0.08em",
        }}>NUTRIINTEL</span>
        <span style={{
          fontSize: "0.65rem", color: "#00FF94", fontFamily: "var(--font-mono)",
          background: "rgba(0,255,148,0.1)", border: "1px solid rgba(0,255,148,0.2)",
          borderRadius: "4px", padding: "1px 6px", letterSpacing: "0.06em",
        }}>v1.0.0</span>
      </div>
      <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
        <a href="#features" style={{ color: "#8B9BB4", textDecoration: "none", fontSize: "0.875rem", transition: "color 0.2s" }}
          onMouseEnter={e => (e.currentTarget.style.color = "#00FF94")}
          onMouseLeave={e => (e.currentTarget.style.color = "#8B9BB4")}>Features</a>
        <a href="#knowledge" style={{ color: "#8B9BB4", textDecoration: "none", fontSize: "0.875rem", transition: "color 0.2s" }}
          onMouseEnter={e => (e.currentTarget.style.color = "#00FF94")}
          onMouseLeave={e => (e.currentTarget.style.color = "#8B9BB4")}>Knowledge</a>
        <a
          href="https://cpna-eval-one.vercel.app"
          target="_blank" rel="noopener noreferrer"
          style={{
            color: "#7C4DFF", textDecoration: "none", fontSize: "0.875rem",
            border: "1px solid rgba(124,77,255,0.3)", borderRadius: "6px",
            padding: "0.35rem 0.85rem", transition: "all 0.2s",
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(124,77,255,0.1)"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
        >Eval Platform</a>
        <Link href="/chat" style={{
          background: "#00FF94", color: "#0A0E1A", textDecoration: "none",
          fontWeight: 700, fontSize: "0.875rem", borderRadius: "6px",
          padding: "0.4rem 1rem",
        }}>Open Assistant →</Link>
      </div>
    </nav>
  );
}

/* ─── Terminal typewriter ─── */
const LINES = [
  "query: 'iron deficiency in preterm neonate'",
  "intent_classified: general  confidence: 0.97",
  "retrieving: vector(20) + bm25(20) → merged(31)",
  "reranked: top_7_contexts selected",
  "response: GeneralCard  latency: 842ms",
];
function Terminal() {
  const [lines, setLines] = useState<string[]>([]);
  const [cursor, setCursor] = useState(true);
  useEffect(() => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < LINES.length) { setLines(prev => [...prev, LINES[i]]); i++; }
      else { clearInterval(interval); }
    }, 900);
    return () => clearInterval(interval);
  }, []);
  useEffect(() => {
    const t = setInterval(() => setCursor(c => !c), 500);
    return () => clearInterval(t);
  }, []);
  return (
    <div style={{
      background: "#070B14", border: "1px solid rgba(0,255,148,0.2)",
      borderRadius: "12px", padding: "1.25rem 1.5rem",
      fontFamily: "var(--font-mono)", fontSize: "0.78rem",
      minHeight: "160px", animation: "fadeUp 0.8s ease 0.5s both",
    }}>
      <div style={{ display: "flex", gap: "6px", marginBottom: "0.75rem" }}>
        {["#FF5F56","#FFBD2E","#27C93F"].map((c, i) => (
          <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c }}/>
        ))}
        <span style={{ color: "#4A5878", marginLeft: "0.5rem", fontSize: "0.72rem" }}>nutriintel-api — live</span>
      </div>
      {lines.map((line, i) => (
        <div key={i} style={{ marginBottom: "0.35rem" }}>
          <span style={{ color: "#4A5878" }}>› </span>
          <span style={{ color: i % 2 === 0 ? "#00FF94" : "#8B9BB4" }}>{line}</span>
        </div>
      ))}
      {cursor && <span style={{ color: "#00FF94" }}>█</span>}
    </div>
  );
}

/* ─── Main landing page ─── */
export default function LandingPage() {
  return (
    <div style={{ position: "relative", minHeight: "100vh", overflowX: "hidden" }}>
      <GridBackground />
      <Navbar />

      {/* ── Hero ── */}
      <section style={{
        position: "relative", zIndex: 1,
        minHeight: "100vh",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        padding: "8rem 1.5rem 4rem",
        textAlign: "center",
      }}>
        {/* Badge */}
        <div style={{
          animation: "fadeUp 0.5s ease both",
          display: "inline-flex", alignItems: "center", gap: "0.5rem",
          background: "rgba(0,255,148,0.06)", border: "1px solid rgba(0,255,148,0.2)",
          borderRadius: "999px", padding: "0.35rem 1rem", marginBottom: "2rem",
        }}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#00FF94", display: "inline-block", boxShadow: "0 0 8px #00FF94" }}/>
          <span style={{ color: "#00FF94", fontFamily: "var(--font-mono)", fontSize: "0.75rem", letterSpacing: "0.08em" }}>
            AGENTIC RAG · PEDIATRIC CLINICAL NUTRITION
          </span>
        </div>

        {/* Logo + wordmark */}
        <div style={{ animation: "fadeUp 0.5s ease 0.1s both", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "1rem", justifyContent: "center" }}>
          <div style={{ animation: "pulse-glow 3s ease-in-out infinite" }}>
            <NutriIntelLogo size={64} />
          </div>
          <div style={{ textAlign: "left" }}>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "2rem", fontWeight: 800, color: "#E8EDF5", letterSpacing: "0.1em" }}>NUTRIINTEL</div>
            <div style={{ color: "#8B9BB4", fontSize: "0.8rem", fontFamily: "var(--font-mono)", letterSpacing: "0.12em" }}>CLINICAL PEDIATRIC NUTRITION ASSISTANT</div>
          </div>
        </div>

        {/* Headline */}
        <h1 style={{
          fontSize: "clamp(2rem, 5vw, 3.5rem)", fontWeight: 800,
          lineHeight: 1.15, maxWidth: "760px", marginBottom: "1.25rem",
          fontFamily: "var(--font-display)",
          background: "linear-gradient(135deg, #E8EDF5 0%, #00FF94 50%, #7C4DFF 100%)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          backgroundSize: "200% auto",
          animation: "shimmer 4s linear infinite, fadeUp 0.6s ease 0.2s both",
        }}>
          Evidence-Based Pediatric Nutrition Intelligence
        </h1>

        <p style={{
          animation: "fadeUp 0.6s ease 0.35s both",
          color: "#8B9BB4", fontSize: "1.1rem", maxWidth: "580px",
          lineHeight: 1.65, marginBottom: "2.5rem",
        }}>
          An agentic AI system trained on international clinical guidelines and food composition databases —
          delivering structured, retrievable answers for complex pediatric nutrition queries.
        </p>

        {/* CTA buttons */}
        <div style={{
          animation: "fadeUp 0.6s ease 0.45s both",
          display: "flex", gap: "1rem", flexWrap: "wrap", justifyContent: "center",
          marginBottom: "4rem",
        }}>
          <Link href="/chat" style={{
            display: "inline-flex", alignItems: "center", gap: "0.5rem",
            background: "#00FF94", color: "#0A0E1A",
            textDecoration: "none", fontWeight: 800, fontSize: "1rem",
            borderRadius: "10px", padding: "0.85rem 2rem",
            transition: "all 0.2s", boxShadow: "0 0 30px rgba(0,255,148,0.3)",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 50px rgba(0,255,148,0.5)"; (e.currentTarget as HTMLElement).style.transform = "scale(1.03)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 30px rgba(0,255,148,0.3)"; (e.currentTarget as HTMLElement).style.transform = "scale(1)"; }}
          >
            <span>Open Assistant</span>
            <span>→</span>
          </Link>
          <a href="https://cpna-eval-one.vercel.app" target="_blank" rel="noopener noreferrer" style={{
            display: "inline-flex", alignItems: "center", gap: "0.5rem",
            background: "transparent", color: "#7C4DFF",
            textDecoration: "none", fontWeight: 700, fontSize: "1rem",
            borderRadius: "10px", padding: "0.85rem 2rem",
            border: "1px solid rgba(124,77,255,0.4)",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(124,77,255,0.1)"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
          >
            <span>⚡ AI Eval Platform</span>
          </a>
        </div>

        {/* Stats row */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: "1rem", maxWidth: "640px", width: "100%", marginBottom: "4rem",
        }}>
          <StatCard value="4" label="Query Types" delay={500} />
          <StatCard value="11+" label="Conditions" delay={600} />
          <StatCard value="98.6%" label="Intent F1" delay={700} />
          <StatCard value="Top 7" label="Retrieval K" delay={800} />
        </div>

        {/* Hero illustration */}
        <div style={{ animation: "fadeIn 1s ease 0.8s both", maxWidth: 520, width: "100%" }}>
          <MoleculeIllustration />
        </div>
      </section>

      {/* ── Terminal / Live demo strip ── */}
      <section style={{
        position: "relative", zIndex: 1,
        padding: "4rem 1.5rem",
        background: "linear-gradient(180deg, transparent, rgba(0,255,148,0.02), transparent)",
      }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "2rem" }}>
            <h2 style={{ color: "#E8EDF5", fontFamily: "var(--font-mono)", fontSize: "1.1rem", letterSpacing: "0.08em", marginBottom: "0.5rem" }}>
              <span style={{ color: "#00FF94" }}>$</span> LIVE PIPELINE
            </h2>
            <p style={{ color: "#8B9BB4", fontSize: "0.875rem" }}>Every query flows through retrieval, reranking, and structured output</p>
          </div>
          <Terminal />
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" style={{ position: "relative", zIndex: 1, padding: "5rem 1.5rem" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "3rem" }}>
            <div style={{ color: "#00FF94", fontFamily: "var(--font-mono)", fontSize: "0.75rem", letterSpacing: "0.12em", marginBottom: "0.75rem" }}>
              PLATFORM CAPABILITIES
            </div>
            <h2 style={{ color: "#E8EDF5", fontSize: "clamp(1.6rem, 3vw, 2.2rem)", fontWeight: 800, fontFamily: "var(--font-display)" }}>
              Built for Clinical Precision
            </h2>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.25rem" }}>
            <FeatureCard delay={0} icon="🧠" title="Agentic Intent Classification"
              body="A fine-tuned sentence-transformer + logistic regression model classifies every query into Therapy, Recommendation, Comparison, or General — with 98.6% F1 and explicit fallback on low-confidence inputs." />
            <FeatureCard delay={100} icon="🔍" title="Hybrid Retrieval Pipeline"
              body="Vector search (Qdrant) + BM25 lexical search run in parallel across 20 candidates each, then merge, deduplicate, and rerank to the top 7 highest-relevance clinical contexts." accent="#7C4DFF" />
            <FeatureCard delay={200} icon="🛡️" title="Therapy Gatekeeper"
              body="Personalized nutrition plans require all clinical slots (age, weight, height, sex, diagnosis, medications, biomarkers, country). Missing data triggers structured slot-filling — never hallucinated targets." />
            <FeatureCard delay={300} icon="🧬" title="Deterministic Nutrient Engine"
              body="Macro and micronutrient targets are computed from validated DRI tables using linear programming optimization — not generated by the LLM. Every target traces to a clinical reference." accent="#FFB547" />
            <FeatureCard delay={400} icon="🌍" title="West African & Global FCT Coverage"
              body="Food composition data spans local staples from West Africa, East Africa, South Asia, and global databases — enabling culturally appropriate, geographically grounded recommendations." />
            <FeatureCard delay={500} icon="⚡" title="AI Evaluation Suite"
              body="A dedicated evaluation platform scores every response across 5 dimensions: intent accuracy, gatekeeper correctness, contract fidelity, context safety, and retrieval quality — with 10 E2E scenarios." accent="#7C4DFF" />
          </div>
        </div>
      </section>

      {/* ── Knowledge base ── */}
      <section id="knowledge" style={{
        position: "relative", zIndex: 1, padding: "5rem 1.5rem",
        background: "linear-gradient(180deg, transparent, rgba(15,21,37,0.6), transparent)",
      }}>
        <div style={{ maxWidth: 900, margin: "0 auto", textAlign: "center" }}>
          <div style={{ color: "#00FF94", fontFamily: "var(--font-mono)", fontSize: "0.75rem", letterSpacing: "0.12em", marginBottom: "0.75rem" }}>
            KNOWLEDGE BASE
          </div>
          <h2 style={{ color: "#E8EDF5", fontSize: "clamp(1.6rem, 3vw, 2.2rem)", fontWeight: 800, fontFamily: "var(--font-display)", marginBottom: "1rem" }}>
            Grounded in Clinical Literature
          </h2>
          <p style={{ color: "#8B9BB4", lineHeight: 1.7, maxWidth: 620, margin: "0 auto 2.5rem" }}>
            NutriIntel retrieves from a curated corpus of international clinical nutrition guidelines,
            dietary reference intake standards, drug–nutrient interaction handbooks, pediatric dietetics textbooks,
            and regional food composition tables — spanning multiple continents.
          </p>

          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "0.25rem", marginBottom: "2.5rem" }}>
            <SourcePill label="International DRI Standards" color="#00FF94" />
            <SourcePill label="Pediatric Dietetics Texts" color="#7C4DFF" />
            <SourcePill label="Clinical Nutrition Handbooks" color="#00FF94" />
            <SourcePill label="Drug–Nutrient Interactions" color="#FFB547" />
            <SourcePill label="West Africa Food Composition" color="#00FF94" />
            <SourcePill label="Preterm & Neonatal Guidelines" color="#7C4DFF" />
            <SourcePill label="Biochemistry References" color="#FFB547" />
            <SourcePill label="East & Central Africa FCT" color="#00FF94" />
            <SourcePill label="Multicultural Food Handbook" color="#7C4DFF" />
            <SourcePill label="Global Dietary Guidelines" color="#00FF94" />
          </div>

          {/* Knowledge architecture visual */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "1rem", marginTop: "2rem",
          }}>
            {[
              { label: "PDF Loader", detail: "Structured extraction from clinical PDFs", color: "#00FF94" },
              { label: "Chapter Extractor", detail: "Section-level passage chunking by document type", color: "#7C4DFF" },
              { label: "Metadata Enricher", detail: "Condition tags, age relevance, therapy area", color: "#FFB547" },
              { label: "Semantic Embedder", detail: "all-MiniLM-L6-v2 vector representations", color: "#00FF94" },
            ].map((item, i) => (
              <div key={i} style={{
                padding: "1.25rem", background: "rgba(15,21,37,0.8)",
                border: `1px solid ${item.color}22`, borderRadius: "12px",
                textAlign: "left",
                animation: `fadeUp 0.5s ease ${i * 100}ms both`,
              }}>
                <div style={{ color: item.color, fontFamily: "var(--font-mono)", fontSize: "0.75rem", marginBottom: "0.5rem", letterSpacing: "0.06em" }}>
                  {item.label}
                </div>
                <div style={{ color: "#8B9BB4", fontSize: "0.8rem", lineHeight: 1.5 }}>{item.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Eval platform callout ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "5rem 1.5rem" }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <div style={{
            padding: "3rem",
            background: "linear-gradient(135deg, rgba(124,77,255,0.1) 0%, rgba(0,255,148,0.05) 100%)",
            border: "1px solid rgba(124,77,255,0.3)",
            borderRadius: "20px",
            textAlign: "center",
            position: "relative", overflow: "hidden",
          }}>
            {/* Corner glow */}
            <div style={{
              position: "absolute", top: -60, right: -60, width: 200, height: 200,
              background: "radial-gradient(circle, rgba(124,77,255,0.2), transparent 70%)",
              pointerEvents: "none",
            }}/>
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚡</div>
            <h2 style={{ color: "#E8EDF5", fontSize: "1.6rem", fontWeight: 800, fontFamily: "var(--font-display)", marginBottom: "0.75rem" }}>
              AI Evaluation Suite
            </h2>
            <p style={{ color: "#8B9BB4", lineHeight: 1.7, maxWidth: 560, margin: "0 auto 1.5rem" }}>
              Test, score, and monitor every layer of NutriIntel — from intent classification and therapy gating
              to retrieval quality and context safety. 10 E2E scenarios across 4 query types and 5 eval dimensions.
            </p>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", justifyContent: "center", marginBottom: "2rem" }}>
              {["THERAPY","RECOMMENDATION","COMPARISON","GENERAL"].map(t => (
                <span key={t} style={{
                  padding: "0.3rem 0.75rem", borderRadius: "6px",
                  border: "1px solid rgba(0,255,148,0.3)",
                  color: "#00FF94", fontSize: "0.75rem", fontFamily: "var(--font-mono)",
                  background: "rgba(0,255,148,0.05)",
                }}>{t}</span>
              ))}
            </div>
            <a href="https://cpna-eval-one.vercel.app" target="_blank" rel="noopener noreferrer" style={{
              display: "inline-flex", alignItems: "center", gap: "0.5rem",
              background: "#7C4DFF", color: "#fff",
              textDecoration: "none", fontWeight: 700, fontSize: "0.95rem",
              borderRadius: "10px", padding: "0.8rem 2rem",
              transition: "all 0.2s", boxShadow: "0 0 24px rgba(124,77,255,0.3)",
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 40px rgba(124,77,255,0.5)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 24px rgba(124,77,255,0.3)"; }}
            >
              Open Eval Platform →
            </a>
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "5rem 1.5rem 8rem", textAlign: "center" }}>
        <h2 style={{
          color: "#E8EDF5", fontSize: "clamp(1.8rem, 4vw, 2.8rem)", fontWeight: 800,
          fontFamily: "var(--font-display)", marginBottom: "1rem",
        }}>
          Ready to ask your first question?
        </h2>
        <p style={{ color: "#8B9BB4", fontSize: "1rem", marginBottom: "2rem" }}>
          No sign-up required. Just ask about pediatric nutrition.
        </p>
        <Link href="/chat" style={{
          display: "inline-flex", alignItems: "center", gap: "0.6rem",
          background: "#00FF94", color: "#0A0E1A",
          textDecoration: "none", fontWeight: 800, fontSize: "1.1rem",
          borderRadius: "12px", padding: "1rem 2.5rem",
          boxShadow: "0 0 40px rgba(0,255,148,0.35)",
          transition: "all 0.2s",
        }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 60px rgba(0,255,148,0.55)"; (e.currentTarget as HTMLElement).style.transform = "scale(1.04)"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = "0 0 40px rgba(0,255,148,0.35)"; (e.currentTarget as HTMLElement).style.transform = "scale(1)"; }}
        >
          Start with NutriIntel →
        </Link>
      </section>

      {/* ── Footer ── */}
      <footer style={{
        position: "relative", zIndex: 1,
        borderTop: "1px solid rgba(30,45,74,0.5)",
        padding: "1.5rem 2rem",
        display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap",
        gap: "1rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <NutriIntelLogo size={22} />
          <span style={{ color: "#4A5878", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>NutriIntel v1.0.0 · CPNA Clinical Pediatric Nutrition Assistant</span>
        </div>
        <div style={{ display: "flex", gap: "1.5rem" }}>
          <a href="https://cpna-eval-one.vercel.app" target="_blank" rel="noopener noreferrer"
            style={{ color: "#4A5878", textDecoration: "none", fontSize: "0.8rem", transition: "color 0.2s" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#7C4DFF")}
            onMouseLeave={e => (e.currentTarget.style.color = "#4A5878")}>Eval Platform</a>
          <Link href="/chat" style={{ color: "#4A5878", textDecoration: "none", fontSize: "0.8rem", transition: "color 0.2s" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#00FF94")}
            onMouseLeave={e => (e.currentTarget.style.color = "#4A5878")}>Assistant</Link>
        </div>
      </footer>
    </div>
  );
}
