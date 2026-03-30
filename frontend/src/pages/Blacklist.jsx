import "./Blacklist.css";
import { FiAlertTriangle } from "react-icons/fi";
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
  return (
    <main className="blacklist-page" dir="rtl">
      <div className="blacklist-warning">
        <FiAlertTriangle size={16} />
        <div>
          <span className="warning-label">تحذير: </span>
          <span>جميع البائعين في هذه القائمة تم الإبلاغ عنهم بشكل متكرر من قبل المجتمع. تضمنت شكاوى التقارير عليهم ممارستهم لعمليات نصب متعددة. دائماً تحقق من نقاط الثقة قبل أي عملية شراء.</span>
        </div>
      </div>

      <div className="blacklist-list">
        {MOCK_BLACKLIST.map((seller) => (
          <BlacklistCard
            key={seller.id}
            username={seller.username}
            location={seller.location}
            score={seller.score}
            aiSummary={seller.aiSummary}
          />
        ))}
      </div>
    </main>
  );
}