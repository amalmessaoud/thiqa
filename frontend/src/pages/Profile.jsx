import "./Profile.css";
import { useState } from "react";
import { FiStar, FiFlag } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import ReportCard from "../components/ReportCard";
import ReviewCard from "../components/ReviewCard";

const MOCK_REVIEWS = [
  {
    id: 1,
    seller: "متجر الإلكترونيات",
    initials: "مت",
    rating: 5,
    tags: ["أشتري مرة أخرى", "رد سريع", "وصل", "طابق الإعلان"],
    comment: "بائع ممتاز، المنتج وصل في الوقت والجودة ممتازة. أنصح بالتعامل معه 👍",
    date: "2026-03-22",
  },
  {
    id: 2,
    seller: "متجر الإكسسوارات",
    initials: "مإ",
    rating: 4,
    tags: ["طابق الإعلان", "رد سريع", "وصل"],
    comment: "المنتج جيد، لكن السعر كان شوية غالي.",
    date: "2026-03-01",
  },
];

const MOCK_REPORTS = [
  {
    id: 1,
    seller: "بائع مشبوه 1",
    initials: "بم",
    type: "لم تصل البضاعة",
    risk: "خطر عالي",
    comment: "حولتلو 15000 دج على CCP وما وصلتنيش البضاعة. بلوكاني على واتساب وفيسبوك.",
    date: "2026-03-20",
    proof: "https://picsum.photos/400/300",
  },
  {
    id: 2,
    seller: "بائع الإلكترونيات",
    initials: "بإ",
    type: "منتج مزيف",
    risk: "متوسط",
    comment: "المنتج لا وصل مزيف وجودة رديئة. ما هوش كيما الصور.",
    date: "2026-03-10",
    proof: "https://picsum.photos/400/300",
  },
  {
    id: 3,
    seller: "بائع العطور",
    initials: "بع",
    type: "جودة رديئة",
    risk: "منخفض",
    comment: "الجودة ما كانتش كيما توقعت، لكن البائع رد وحل المشكلة.",
    date: "2026-02-28",
    proof: "https://picsum.photos/400/300",
  },
];

export default function Profile() {
  const { user } = useAuth();
  const [tab, setTab] = useState("reviews");

  return (
    <main className="profile-page" dir="rtl">
      <div className="profile-user-card">
        <div className="profile-avatar">
          {user?.name?.slice(0, 2) || "MA"}
        </div>
        <p className="profile-name">{user?.name || "محمد أحمد"}</p>
      </div>

      <div className="profile-tabs">
        <button
          className={`profile-tab ${tab === "reviews" ? "active" : ""}`}
          onClick={() => setTab("reviews")}
        >
          <FiStar size={14} /> تقييماتي ({MOCK_REVIEWS.length})
        </button>
        <button
          className={`profile-tab ${tab === "reports" ? "active" : ""}`}
          onClick={() => setTab("reports")}
        >
          <FiFlag size={14} /> تقاريري ({MOCK_REPORTS.length})
        </button>
      </div>

      {tab === "reviews" && (
        <div className="profile-section">
          <h2>سجل التقييمات</h2>
          <div className="profile-list">
            {MOCK_REVIEWS.map((r) => (
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
        </div>
      )}

      {tab === "reports" && (
        <div className="profile-section">
          <h2>سجل التقارير</h2>
          <div className="profile-list">
            {MOCK_REPORTS.map((r) => (
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
        </div>
      )}
    </main>
  );
}