import "./Blacklist.css";
import { useState, useEffect } from "react";
import { FiAlertTriangle } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import BlacklistCard from "../components/BlacklistCard";

const MOCK_BLACKLIST = [
  {
    id: 1,
    username: "@luxury_watches_dz",
    location: "الجزائر العاصمة",
    score: 34,
    aiSummary: "يبيع منتجات إلكترونية مزيفة بأسعار مغرية. المنتجات التي تصل تكون موبقة رديئة وغير أصلية. الصور في الإعلانات مسروقة من مواقع عالمية. العملاء يشتكون من عدم الرد بعد البيع.",
  },
  {
    id: 2,
    username: "@fake_electronics_dz",
    location: "وهران",
    score: 18,
    aiSummary: "تم الإبلاغ عنه من طرف أكثر من 20 مشتري. يأخذ المال ولا يرسل البضاعة. يستخدم حسابات متعددة للتهرب من الإبلاغات.",
  },
  {
    id: 3,
    username: "@scammer_constantine",
    location: "قسنطينة",
    score: 22,
    aiSummary: "يبيع منتجات مزيفة بأسعار مغرية جداً. الصور مسروقة من مواقع أجنبية. لا يرد على الرسائل بعد استلام الدفع.",
  },
];

export default function Blacklist() {
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    thiqaApi.getBlacklist()
      .then((data) => {
        if (data && data.length > 0) {
          setBlacklist(data);
        } else {
          setBlacklist(MOCK_BLACKLIST);
        }
      })
      .catch(() => setBlacklist(MOCK_BLACKLIST))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="blacklist-page" dir="rtl">
      <div className="blacklist-warning">
        <FiAlertTriangle size={16} />
        <div>
          <span className="warning-label">تحذير: </span>
          <span>جميع البائعين في هذه القائمة تم الإبلاغ عنهم بشكل متكرر من قبل المجتمع. تضمنت شكاوى التقارير عليهم ممارستهم لعمليات نصب متعددة. دائماً تحقق من نقاط الثقة قبل أي عملية شراء.</span>
        </div>
      </div>

      {loading ? (
        <div className="blacklist-loading">جاري التحميل...</div>
      ) : (
        <div className="blacklist-list">
          {blacklist.map((seller, index) => (
            <BlacklistCard
              key={seller.id || index}
              username={seller.username || seller.display_name}
              location={seller.location}
              score={seller.score || seller.trust_score?.score}
              aiSummary={seller.aiSummary || seller.trust_score?.verdict_narrative}
            />
          ))}
        </div>
      )}
    </main>
  );
}