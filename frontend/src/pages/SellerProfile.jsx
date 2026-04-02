import "./SellerProfile.css";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FiFlag, FiStar, FiActivity } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import TrustScore from "../components/TrustScore";
import SellerInfo from "../components/SellerInfo";
import AiVerdict from "../components/AiVerdict";
import ReportCard from "../components/ReportCard";
import ReviewCard from "../components/ReviewCard";
import PrimaryButton from "../components/PrimaryButton";
import { thiqaApi } from "../api/thiqa";

function formatAge(days) {
  if (!days) return "غير معروف";
  if (days < 30) return `${days} يوم`;
  if (days < 365) return `${Math.floor(days / 30)} شهر`;
  const years = Math.floor(days / 365);
  const months = Math.floor((days % 365) / 30);
  if (months === 0) return `${years} سنة`;
  return `${years} سنة و ${months} شهر`;
}

export default function SellerProfile() {
  console.log("Seller ID from URL:", sellerId);

  const navigate = useNavigate();
  const { sellerId } = useParams();
  const [tab, setTab] = useState("reviews");
  const [data, setData] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sellerId) return;
    setLoading(true);
    thiqaApi
      .search(decodeURIComponent(sellerId))
      .then((result) => {
        if (result?.found) {
          setData(result);
          setReviews(result.reviews || []);
          setReports(result.reports || []);
        } else {
          setError("لم يتم العثور على البائع");
        }
      })
      .catch(() => setError("حدث خطأ أثناء تحميل البيانات"))
      .finally(() => setLoading(false));
  }, [sellerId]);

  if (loading)
    return (
      <main className="seller-page" dir="rtl">
        <div className="seller-loading">جاري التحميل...</div>
      </main>
    );
  if (error)
    return (
      <main className="seller-page" dir="rtl">
        <div className="seller-error">{error}</div>
      </main>
    );
  if (!data) return null;

  const seller = data.seller;
  const trust = data.trust_score;
  const phone = seller?.contacts?.find((c) => c.type === "phone")?.value;
  const fbLink =
    seller?.contacts?.find((c) => c.type === "facebook")?.value ||
    seller?.profile_url;

  useEffect(() => {
    if (!sellerId) return;
    setLoading(true);
    setError("");
    thiqaApi
      .search({ query: sellerId }) // search API returns seller data
      .then((data) => {
        if (!data?.found || !data?.seller) {
          setError("لم يتم العثور على البائع");
        } else {
          setSeller(data.seller);
        }
      })
      .catch(() => setError("حدث خطأ أثناء جلب بيانات البائع"))
      .finally(() => setLoading(false));
  }, [sellerId]);

  console.log("SELLER:", seller);
  return (
    <main className="seller-page" dir="rtl">
      <div className="seller-header">
        <div className="seller-header-left">
          <h1>{seller?.display_name || seller?.profile_url}</h1>
          <p>📍 {seller?.platform || "facebook"}</p>
        </div>
        <TrustScore score={trust?.score} />
      </div>

      {trust?.verdict_narrative && <AiVerdict text={trust.verdict_narrative} />}

      <SellerInfo
        phone={phone}
        username={seller?.display_name}
        fbLink={fbLink}
      />

      <div className="seller-card">
        <h3>تحليل الحساب</h3>
        <div className="seller-fb-rows">
          <div className="seller-fb-row">
            <span>عمر الحساب</span>
            <span>{formatAge(seller?.account_age_days)}</span>
          </div>
          <div className="seller-fb-row">
            <span>عدد المنشورات</span>
            <span>{seller?.post_count}</span>
          </div>
          <div className="seller-fb-row">
            <span>المنصة</span>
            <span>{seller?.platform}</span>
          </div>
        </div>
      </div>

      <div className="seller-stats">
        <div className="stat-box">
          <FiActivity size={22} color="#122040" />
          <p className="stat-number">{reviews.length + reports.length}</p>
          <p className="stat-label">تفاعل</p>
        </div>
        <div className="stat-box">
          <FiFlag size={22} color="#e53e3e" />
          <p className="stat-number">{reports.length}</p>
          <p className="stat-label">تقرير نصب</p>
        </div>
        <div className="stat-box">
          <FiStar size={22} color="#1D9E75" />
          <p className="stat-number">{reviews.length}</p>
          <p className="stat-label">تقييم</p>
        </div>
      </div>

      <div className="seller-tabs">
        <button
          className={`tab-btn ${tab === "reviews" ? "active" : ""}`}
          onClick={() => setTab("reviews")}
        >
          التقييمات ({reviews.length})
        </button>
        <button
          className={`tab-btn ${tab === "reports" ? "active" : ""}`}
          onClick={() => setTab("reports")}
        >
          التقارير ({reports.length})
        </button>
      </div>

      {tab === "reviews" && (
        <>
          {reviews.length === 0 && (
            <p className="no-data">لا توجد تقييمات بعد</p>
          )}
          {reviews.map((r, i) => (
            <ReviewCard
              key={r.id || i}
              name={r.reviewer_name || "مشتري"}
              initials={r.reviewer_name?.slice(0, 2) || "م"}
              date={r.created_at?.slice(0, 10)}
              rating={r.stars || r.rating}
              tags={r.tags || []}
              comment={r.comment}
            />
          ))}
        </>
      )}

      {tab === "reports" && (
        <>
          {reports.length === 0 && (
            <p className="no-data">لا توجد تقارير بعد</p>
          )}
          {reports.map((r, i) => (
            <ReportCard
              key={r.id || i}
              name="مشتري مجهول"
              date={r.created_at?.slice(0, 10)}
              type={r.scam_type}
              risk={r.credibility_label || "غير محدد"}
              comment={r.description}
              proof={r.screenshot_url}
            />
          ))}
        </>
      )}

      <div className="seller-actions">
        <PrimaryButton
          fullWidth
          variant="red"
          onClick={() => navigate("/report")}
        >
          <FiFlag size={16} /> إبلاغ عن هذا البائع
        </PrimaryButton>
        <PrimaryButton
          fullWidth
          variant="green"
          onClick={() => navigate(`/review/${sellerId}`)}
        >
          <FiStar size={16} /> ترك تقييم
        </PrimaryButton>
      </div>
    </main>
  );
}
