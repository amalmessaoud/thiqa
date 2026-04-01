import "./ReportCard.css";
import { useState } from "react";
import { FiFlag, FiImage, FiX } from "react-icons/fi";

export default function ReportCard({ name, initials, date, type, risk, comment, proof }) {
  const [showProof, setShowProof] = useState(false);

  return (
    <>
      <div className="report-card-item">
        <div className="report-card-top">
          {initials ? (
            <div className="report-card-avatar">{initials}</div>
          ) : (
            <div className="report-card-icon">
              <FiFlag size={18} />
            </div>
          )}
          <div className="report-card-info">
            <p className="report-card-name">{name}</p>
            <p className="report-card-date">{date}</p>
          </div>
        </div>

        <div className="report-card-meta">
          <span className="report-card-type">{type}</span>
        </div>

        <p className="report-card-comment">{comment}</p>

        {proof && (
          <button className="proof-btn" onClick={() => setShowProof(true)}>
            <FiImage size={14} /> عرض الدليل
          </button>
        )}
      </div>

      {showProof && (
        <div className="proof-overlay" onClick={() => setShowProof(false)}>
          <div className="proof-modal" onClick={(e) => e.stopPropagation()}>
            <div className="proof-modal-header">
              <button className="proof-close" onClick={() => setShowProof(false)}>
                <FiX size={20} />
              </button>
              <p>الدليل المرفق</p>
            </div>
            <img src={proof} alt="proof" className="proof-image" />
          </div>
        </div>
      )}
    </>
  );
}