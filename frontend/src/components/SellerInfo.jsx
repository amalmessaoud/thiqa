import "./SellerInfo.css";
import { FiPhone, FiUser, FiLink } from "react-icons/fi";

export default function SellerInfo({ phone, username, fbLink }) {
  return (
    <div className="seller-info-card">
      <h3>معلومات البائع</h3>
      <div className="seller-info-rows">
        {phone && (
          <div className="seller-info-row">
            <span>{phone}</span>
            <span className="seller-info-icon"><FiPhone size={14} /></span>
          </div>
        )}
        {username && (
          <div className="seller-info-row">
            <span>{username}</span>
            <span className="seller-info-icon"><FiUser size={14} /></span>
          </div>
        )}
        {fbLink && (
          <div className="seller-info-row">
            <a href={`https://${fbLink}`} target="_blank" rel="noreferrer">{fbLink}</a>
            <span className="seller-info-icon"><FiLink size={14} /></span>
          </div>
        )}
      </div>
    </div>
  );
}