import "./Blacklist.css";
import { useState, useEffect } from "react";
import { FiAlertTriangle } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import BlacklistCard from "../components/BlacklistCard";
import { useNavigate } from "react-router-dom"; // ✅ add this

export default function Blacklist() {
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => {
    thiqaApi
      .getBlacklist()
      .then((data) => {
        if (data?.results?.length > 0) {
          // Map API fields to the props your BlacklistCard expects
          const mapped = data.results.map((seller) => ({
            id: seller.id,
            username: seller.display_name || seller.profile_url, // fallback to URL if display_name missing
            location: seller.category || "غير محدد", // fallback if category missing
            score: seller.report_count, // or compute a score if you want
            aiSummary: `آخر تقرير: ${new Date(seller.latest_report).toLocaleDateString()} - أنواع الاحتيال: ${seller.scam_types.join(", ")}`,
          }));
          setBlacklist(mapped);
        } else {
          setBlacklist([]);
        }
      })
      .catch(() => setBlacklist([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="blacklist-page" dir="rtl">
      <div className="blacklist-warning">
        <FiAlertTriangle size={16} />
        <div>
          <span className="warning-label">تحذير: </span>
          <span>
            جميع البائعين في هذه القائمة تم الإبلاغ عنهم بشكل متكرر من قبل
            المجتمع. دائماً تحقق من نقاط الثقة قبل أي عملية شراء.
          </span>
        </div>
      </div>

      {loading ? (
        <div className="blacklist-loading">جاري التحميل...</div>
      ) : (
        <div className="blacklist-list">
          {blacklist.length === 0 ? (
            <p>لا توجد نتائج في القائمة السوداء حالياً.</p>
          ) : (
            blacklist.map((seller) => (
              <BlacklistCard
                key={seller.id}
                username={seller.username}
                location={seller.location}
                score={seller.score}
                aiSummary={seller.aiSummary}
                onViewProfile={() =>
                  navigate(`/seller/${encodeURIComponent(seller.username)}`)
                }
              />
            ))
          )}
        </div>
      )}
    </main>
  );
}
