import "./SellerProfile.css";
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FiFlag, FiStar, FiActivity } from "react-icons/fi";
import TrustScore from "../components/TrustScore";
import SellerInfo from "../components/SellerInfo";
import AiVerdict from "../components/AiVerdict";
import ReportCard from "../components/ReportCard";
import ReviewCard from "../components/ReviewCard";
import PrimaryButton from "../components/PrimaryButton";
import { thiqaApi } from "../api/thiqa";

const MOCK = {
  name: "seller.dz",
  location: "الجزائر العاصمة",
  score: 68,
  verdict:
    "الغالبية العظمى من التقييمات كانت إيجابية، حيث وصف المشترون تجربتهم بالجيدة والممتازة، وأشادوا بخدمة العملاء والشحن السريع والتغليف الجيد. هناك بعض التقييمات السلبية التي ذكرت مشاكل في الشحن والتأخير والجودة.",
  phone: "0550123456",
  username: "@sellerdz",
  fbLink: "facebook.com/seller.page.dz",
  fb: {
    age: "6 أشهر",
    posts: 78,
    shipping: "متوسط",
    lastActive: "قبل 3 أيام",
    positive: "65%",
    negative: "12%",
  },
  images: { original: 65, suspicious: 2, aiRisk: "منخفض" },
  stats: { reports: 1, reviews: 18, transactions: 124 },
  reviewsList: [
    {
      id: 1,
      name: "محمد أحمد",
      initials: "MA",
      date: "2026-03-22",
      rating: 4,
      tags: ["أشتري مرة أخرى", "رد سريع", "وصل", "طابق الإعلان"],
      comment: "البائع جيد، المنتج وصل لكن التغليف كان ضعيفاً قليلاً",
    },
  ],
  reportsList: [
    {
      id: 1,
      name: "مشتري مجهول",
      date: "2026-02-10",
      type: "جودة رديئة",
      risk: "منخفض",
      comment: "الجودة ما كانتش كيما توقعت، لكن البائع رد وحل المشكلة.",
      proof: "https://picsum.photos/400/300",
    },
  ],
};

export default function SellerProfile() {
  const { sellerId } = useParams(); // get seller id from URL
  console.log("Seller ID from URL:", sellerId);
  const [seller, setSeller] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const navigate = useNavigate();
  const [tab, setTab] = useState("reviews");

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
          <h1>{seller?.name}</h1>
          <p>📍 {seller?.location}</p>
        </div>
        <TrustScore score={seller?.score} />
      </div>

      <AiVerdict text={seller?.verdict} />

      <SellerInfo
        phone={seller?.phone}
        username={seller?.username}
        fbLink={seller?.fbLink}
      />

      <div className="seller-card">
        <h3>تحليل فيسبوك</h3>
        <div className="seller-fb-rows">
          <div className="seller-fb-row">
            <span>عمر الصفحة</span>
            <span>{seller?.fb.age}</span>
          </div>
          <div className="seller-fb-row">
            <span>عدد المنشورات</span>
            <span>{seller?.fb.posts}</span>
          </div>
          <div className="seller-fb-row">
            <span>النشر</span>
            <span>{seller?.fb.shipping}</span>
          </div>
          <div className="seller-fb-row">
            <span>آخر نشاط</span>
            <span>{seller?.fb.lastActive}</span>
          </div>
          <div className="seller-fb-row">
            <span>تعليقات إيجابية</span>
            <span className="positive">{seller?.fb.positive}</span>
          </div>
          <div className="seller-fb-row">
            <span>تعليقات سلبية</span>
            <span className="negative">{seller?.fb.negative}</span>
          </div>
        </div>
      </div>

      <div className="seller-stats">
        <div className="stat-box">
          <FiActivity size={22} color="#122040" />
          <p className="stat-number">{seller?.stats.transactions}</p>
          <p className="stat-label">معاملة</p>
        </div>
        <div className="stat-box">
          <FiFlag size={22} color="#e53e3e" />
          <p className="stat-number">{seller?.stats.reports}</p>
          <p className="stat-label">تقرير نصب</p>
        </div>
        <div className="stat-box">
          <FiStar size={22} color="#1D9E75" />
          <p className="stat-number">{seller?.stats.reviews}</p>
          <p className="stat-label">تقييم إيجابي</p>
        </div>
      </div>

      <div className="seller-card">
        <h3>تحليل الصور</h3>
        <div className="seller-fb-rows">
          <div className="seller-fb-row">
            <span>صور أصلية</span>
            <span className="positive">{seller?.images.original}</span>
          </div>
          <div className="seller-fb-row">
            <span>صور مشبوهة</span>
            <span className="negative">{seller?.images.suspicious}</span>
          </div>
          <div className="seller-fb-row">
            <span>خطر AI</span>
            <span className="badge-low">منخفض</span>
          </div>
        </div>
      </div>

      <div className="seller-tabs">
        <button
          className={`tab-btn ${tab === "reviews" ? "active" : ""}`}
          onClick={() => setTab("reviews")}
        >
          التقييمات ({seller?.reviewsList.length})
        </button>
        <button
          className={`tab-btn ${tab === "reports" ? "active" : ""}`}
          onClick={() => setTab("reports")}
        >
          التقارير ({seller?.reportsList.length})
        </button>
      </div>

      {tab === "reviews" && (
        <>
          {seller?.reviewsList.map((r) => (
            <ReviewCard
              key={r.id}
              name={r.name}
              initials={r.initials}
              date={r.date}
              rating={r.rating}
              tags={r.tags}
              comment={r.comment}
            />
          ))}
          <button className="load-more-btn">عرض المزيد من التقييمات</button>
        </>
      )}

      {tab === "reports" && (
        <>
          {seller?.reportsList.map((r) => (
            <ReportCard
              key={r.id}
              name={r.name}
              date={r.date}
              type={r.type}
              risk={r.risk}
              comment={r.comment}
              proof={r.proof}
            />
          ))}
          <button className="load-more-btn">عرض المزيد من التقارير</button>
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
          onClick={() => navigate("/review/sellerdz")}
        >
          <FiStar size={16} /> ترك تقييم
        </PrimaryButton>
      </div>
    </main>
  );
}
