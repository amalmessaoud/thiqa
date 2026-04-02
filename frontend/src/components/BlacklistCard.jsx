import "./BlacklistCard.css";
import { useNavigate } from "react-router-dom";
import TrustScore from "./TrustScore";
import AiVerdict from "./AiVerdict";

export default function BlacklistCard({
  username,
  location,
  score,
  aiSummary,
  onViewProfile,
}) {
  return (
    <div className="blacklist-card">
      <h3>{username}</h3>
      <p>{location}</p>
      <p>عدد البلاغات: {score}</p>
      <p>{aiSummary}</p>
      {onViewProfile && (
        <button className="view-profile-btn" onClick={onViewProfile}>
          عرض الملف الكامل للبائع
        </button>
      )}
    </div>
  );
}
