import "./BlacklistCard.css";
import { FiAlertTriangle, FiMapPin, FiFlag, FiExternalLink } from "react-icons/fi";

const SCAM_TYPE_LABELS = {
  no_response: "لم تصل البضاعة",
  fake_product: "منتج مزيف",
  advance_payment: "أخذ المال ولم يرد",
  ghost_seller: "حساب مزيف",
  other: "أخرى",
};

function parseAiSummary(aiSummary) {
  const dateMatch = aiSummary?.match(/آخر تقرير:\s*([^\s—–]+)/);
  const typesMatch = aiSummary?.match(/أنواع الاحتيال:\s*(.+)/);
  const date = dateMatch?.[1] || null;
  const rawTypes = typesMatch?.[1]?.split(",").map((s) => s.trim()) || [];
  const types = rawTypes.map((t) => SCAM_TYPE_LABELS[t] || t);
  return { date, types };
}

export default function BlacklistCard({ username, location, score, aiSummary, onViewProfile }) {
  const { date, types } = parseAiSummary(aiSummary);
  const initial = (username?.[0] || "?").toUpperCase();
  const danger = score >= 5;
  const warning = score >= 2;
  const badgeClass = danger ? "bc-badge-danger" : warning ? "bc-badge-warning" : "bc-badge-low";

  return (
    <div className="bc-card">
      <div className="bc-accent" />
      <div className="bc-body">

        {/* Top: avatar + name + badge */}
        <div className="bc-top">
          <div className="bc-avatar">{initial}</div>
          <div className="bc-info">
            <span className="bc-username">{username}</span>
            {location && location !== "غير محدد" && (
              <span className="bc-location"><FiMapPin size={11} /> {location}</span>
            )}
          </div>
          <div className={`bc-badge ${badgeClass}`}>
            <FiAlertTriangle size={11} />
            {score} {score === 1 ? "بلاغ" : "بلاغات"}
          </div>
        </div>

        {/* Scam type pills */}
        {types.length > 0 && (
          <div className="bc-pills">
            {types.map((t, i) => (
              <span key={i} className="bc-pill"><FiFlag size={10} /> {t}</span>
            ))}
          </div>
        )}

        {/* Date + button row */}
        <div className="bc-bottom">
          {date && <span className="bc-date">آخر بلاغ: {date}</span>}
          <button className="bc-btn" onClick={onViewProfile}>
            <FiExternalLink size={13} /> عرض الملف الكامل
          </button>
        </div>

      </div>
    </div>
  );
}