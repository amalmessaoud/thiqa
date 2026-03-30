import "./BlacklistCard.css";
import { useNavigate } from "react-router-dom";
import TrustScore from "./TrustScore";
import AiVerdict from "./AiVerdict";

export default function BlacklistCard({ username, score, aiSummary }) {
  const navigate = useNavigate();

  return (
    <div className="blacklist-card">
      <div className="blacklist-card-top">
        <div className="blacklist-card-info">
          <p className="blacklist-username">{username}</p>
          <button
            className="blacklist-profile-btn"
            onClick={() => navigate("/seller/sellerdz")}
          >
            عرض الملف
          </button>
        </div>
        <TrustScore score={score} compact />
      </div>
      <AiVerdict text={aiSummary} />
    </div>
  );
}