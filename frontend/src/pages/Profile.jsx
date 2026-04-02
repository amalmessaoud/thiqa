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
  const [error, setError] = useState("");

  const initials = (user?.full_name || user?.email || "NA")
    .slice(0, 2)
    .toUpperCase();

  useEffect(() => {
    if (!user?.id) return;

    setLoading(true);
    setError("");

    thiqaApi
      .getUserHistory(user.id)
      .then((data) => {
        const mappedReviews = data.reviews.map((r) => ({
          id: r.id,
          seller: r.seller_url || "Unknown Seller",
          initials: r.seller_url?.slice(0, 2) || "NA",
          rating: r.stars,
          tags: [
            r.would_buy_again ? "أشتري مرة أخرى" : null,
            r.responded_fast ? "رد سريع" : null,
            r.item_received ? "وصل" : null,
            r.product_matched ? "طابق الإعلان" : null,
          ].filter(Boolean),
          comment: r.comment,
          date: r.created_at,
        }));

        const mappedReports = data.reports.map((r) => ({
          id: r.id,
          seller: r.seller_url || "Unknown Seller",
          initials: r.seller_url?.slice(0, 2) || "NA",
          type: r.scam_type,
          risk:
            r.credibility_score >= 70
              ? "خطر عالي"
              : r.credibility_score >= 40
                ? "متوسط"
                : "منخفض",
          comment: r.description,
          date: r.created_at,
          proof: r.screenshot_url
            ? `http://127.0.0.1:8000${r.screenshot_url}`
            : null,
        }));

        setReviews(mappedReviews);
        setReports(mappedReports);
      })
      .catch(() => setError("حدث خطأ أثناء جلب سجل المستخدم"))
      .finally(() => setLoading(false));
  }, [user?.id]);
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
          {loading ? (
            <p>جاري التحميل...</p>
          ) : reviews.length === 0 ? (
            <p>لم تقم بعد بإضافة أي تقييمات.</p>
          ) : (
            <div className="profile-list">
              {reviews.map((r) => (
                <ReviewCard
                  key={r.id}
                  name={r.seller}
                  initials={r.initials}
                  date={r.date}
                  rating={r.rating}
                  tags={r.tags}
                  comment={r.comment}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {!loading && tab === "reports" && (
        <div className="profile-section">
          <h2>سجل التقارير</h2>
          {loading ? (
            <p>جاري التحميل...</p>
          ) : reports.length === 0 ? (
            <p>لم تقم بعد بإرسال أي تقارير.</p>
          ) : (
            <div className="profile-list">
              {reports.map((r) => (
                <ReportCard
                  key={r.id}
                  name={r.seller}
                  initials={r.initials}
                  date={r.date}
                  type={r.type}
                  risk={r.risk}
                  comment={r.comment}
                  proof={r.proof}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  );
}
