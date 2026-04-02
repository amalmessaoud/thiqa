import "./Profile.css";
import { useState, useEffect } from "react";
import { FiStar, FiFlag } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { thiqaApi } from "../api/thiqa";
import ReportCard from "../components/ReportCard";
import ReviewCard from "../components/ReviewCard";

export default function Profile() {
  const { user } = useAuth();
  const [tab, setTab] = useState("reviews");
  const [reviews, setReviews] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    thiqaApi.getHistory()
      .then((data) => {
        setReviews(data?.reviews || []);
        setReports(data?.reports || []);
      })
      .catch(() => {
        setReviews([]);
        setReports([]);
      })
      .finally(() => setLoading(false));
  }, [user]);

  const initials = user?.email?.slice(0, 2).toUpperCase() || "؟";

  return (
    <main className="profile-page" dir="rtl">
      <div className="profile-user-card">
        <div className="profile-avatar">{initials}</div>
        <p className="profile-name">{user?.email || "المستخدم"}</p>
      </div>

      <div className="profile-tabs">
        <button
          className={`profile-tab ${tab === "reviews" ? "active" : ""}`}
          onClick={() => setTab("reviews")}
        >
          <FiStar size={14} /> تقييماتي ({reviews.length})
        </button>
        <button
          className={`profile-tab ${tab === "reports" ? "active" : ""}`}
          onClick={() => setTab("reports")}
        >
          <FiFlag size={14} /> تقاريري ({reports.length})
        </button>
      </div>

      {loading && <p className="profile-loading">جاري التحميل...</p>}

      {!loading && tab === "reviews" && (
        <div className="profile-section">
          <h2>سجل التقييمات</h2>
          <div className="profile-list">
            {reviews.length === 0 && <p className="no-data">لا توجد تقييمات بعد</p>}
            {reviews.map((r, i) => (
              <ReviewCard
                key={r.id || i}
                name={r.seller_profile_url || "بائع"}
                initials={r.seller_profile_url?.slice(0, 2) || "ب"}
                date={r.created_at?.slice(0, 10)}
                rating={r.stars}
                tags={r.tags || []}
                comment={r.comment}
              />
            ))}
          </div>
        </div>
      )}

      {!loading && tab === "reports" && (
        <div className="profile-section">
          <h2>سجل التقارير</h2>
          <div className="profile-list">
            {reports.length === 0 && <p className="no-data">لا توجد تقارير بعد</p>}
            {reports.map((r, i) => (
              <ReportCard
                key={r.id || i}
                name={r.profile_url || "بائع مجهول"}
                initials={r.profile_url?.slice(0, 2) || "ب"}
                date={r.created_at?.slice(0, 10)}
                type={r.scam_type}
                risk={r.credibility_label || "غير محدد"}
                comment={r.description}
                proof={r.screenshot_url}
              />
            ))}
          </div>
        </div>
      )}
    </main>
  );
}