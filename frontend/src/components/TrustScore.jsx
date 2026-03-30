import "./TrustScore.css";

export default function TrustScore({ score, compact = false }) {
  const color = score >= 70 ? "#1D9E75" : score >= 40 ? "#f5a623" : "#e53e3e";
  const label = score >= 70 ? "موثوق" : score >= 40 ? "احذر" : "خطر";

  if (compact) {
    return (
      <div className="trust-score-compact" style={{ borderColor: color, color }}>
        <span className="trust-score-compact-num">{score}</span>
        <span className="trust-score-compact-label">{label}</span>
      </div>
    );
  }

  return (
    <div className="trust-score-box" style={{ borderColor: color }}>
      <p className="trust-score-label-top">نقاط الثقة</p>
      <p className="trust-score-number" style={{ color }}>{score}</p>
      <p className="trust-score-badge" style={{ color }}>{label}</p>
    </div>
  );
}