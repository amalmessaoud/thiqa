import "./Results.css";
import { useSearchParams, useNavigate } from "react-router-dom";
import { FiAlertTriangle, FiImage, FiFileText, FiEye } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import SearchBar from "../components/SearchBar";
import TrustScore from "../components/TrustScore";
import SellerInfo from "../components/SellerInfo";
import AiVerdict from "../components/AiVerdict";
import logo from "../assets/logo.svg";
import PrimaryButton from "../components/PrimaryButton";

const MOCK = {
  username: "@sellerdz",
  phone: "0550123456",
  fbLink: "facebook.com/seller.page.dz",
  score: 65,
  verdict: "الغالبية العظمى من التقييمات كانت إيجابية، حيث وصف المشترون تجربتهم بالجيدة والممتازة، وأشادوا بخدمة العملاء والشحن السريع والتغليف الجيد. هناك بعض التقييمات السلبية التي ذكرت مشاكل في الشحن والتأخير والجودة.",
  fb: { age: "6 أشهر", posts: 78, shipping: "متوسط", lastActive: "قبل 3 أيام" },
};

export default function Results() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const navigate = useNavigate();
  const { user } = useAuth();

  function handleSellerProfile() {
    navigate("/seller/sellerdz");
  }

  return (
    <main className="results-page" dir="rtl">
      <section className="results-hero">
        <img src={logo} alt="Thiqa" className="results-logo-img" />
        <p className="results-subtitle">تحقق من أي بائع قبل ما تسلك !!</p>
        <SearchBar initialValue={query} />
      </section>

      <section className="results-section">
        <h2>نتائج البحث</h2>

        <SellerInfo phone={MOCK.phone} username={MOCK.username} fbLink={MOCK.fbLink} />

        <div className="results-card">
          <h3>تحليل فيسبوك</h3>
          <div className="fb-rows">
            <div className="fb-row"><span>عمر الصفحة</span><span>{MOCK.fb.age}</span></div>
            <div className="fb-row"><span>عدد المنشورات</span><span>{MOCK.fb.posts}</span></div>
            <div className="fb-row"><span>النشر</span><span>{MOCK.fb.shipping}</span></div>
            <div className="fb-row"><span>آخر نشاط</span><span>{MOCK.fb.lastActive}</span></div>
          </div>
        </div>

        <div className="results-trust-card">
          <TrustScore score={MOCK.score} />
          <AiVerdict text={MOCK.verdict} />
          <PrimaryButton fullWidth variant="green" onClick={handleSellerProfile}>
            <FiEye /> عرض الملف الكامل للبائع
          </PrimaryButton>
        </div>

        <div className="results-report-card" onClick={() => navigate("/report")}>
          <div className="report-icon-small"><FiAlertTriangle size={20} /></div>
          <div>
            <p className="report-title">إبلاغ عن بائع</p>
            <p className="report-sub">ساعد المجتمع بالإبلاغ عن البائعين النصابين</p>
          </div>
        </div>

        <h2>أدوات أخرى</h2>
        <div className="results-tools">
          <div className="tool-card-small" onClick={() => navigate("/analyze")}>
            <div className="tool-icon-small"><FiImage size={18} /></div>
            <div>
              <p className="tool-title">تحليل الصور</p>
              <p className="tool-sub">ارفع صورة محادثة أو إعلان</p>
            </div>
          </div>
          <div className="tool-card-small" onClick={() => navigate("/text-analyze")}>
            <div className="tool-icon-small"><FiFileText size={18} /></div>
            <div>
              <p className="tool-title">تحليل النصوص</p>
              <p className="tool-sub">ألصق أي محادثة أو إعلان</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}