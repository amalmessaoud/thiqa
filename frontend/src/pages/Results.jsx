import "./Results.css";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { FiAlertTriangle, FiImage, FiFileText, FiEye, FiPhone, FiLink } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { thiqaApi } from "../api/thiqa";
import SearchBar from "../components/SearchBar";
import TrustScore from "../components/TrustScore";
import SellerInfo from "../components/SellerInfo";
import AiVerdict from "../components/AiVerdict";
import PrimaryButton from "../components/PrimaryButton";
import logo from "../assets/logo.svg";

export default function Results() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") || "";
  const navigate = useNavigate();
  const { user } = useAuth();

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setError("");
    thiqaApi.search(query)
      .then((data) => setResult(data))
      .catch(() => setError("حدث خطأ أثناء البحث، حاول مرة أخرى"))
      .finally(() => setLoading(false));
  }, [query]);

  const seller = result?.seller;
  const trust = result?.trust_score;

  // Extract phone and fb link from contacts
  const phone = seller?.contacts?.find((c) => c.type === "phone")?.value;
  const fbLink = seller?.contacts?.find((c) => c.type === "facebook")?.value;

  function handleSellerProfile() {
    navigate(`/seller/${seller?.id || "sellerdz"}`);
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

        {/* Loading */}
        {loading && (
          <div className="results-loading">جاري البحث...</div>
        )}

        {/* Error */}
        {error && (
          <div className="results-error">{error}</div>
        )}

        {/* No results */}
        {!loading && result && !result.found && (
          <div className="results-not-found">
            لم يتم العثور على بائع بهذه المعلومات
          </div>
        )}

        {/* Results */}
        {!loading && result?.found && seller && (
          <>
            <SellerInfo
              phone={phone}
              username={seller.display_name}
              fbLink={fbLink || seller.profile_url}
            />

            <div className="results-card">
              <h3>🔗 تحليل فيسبوك</h3>
              <div className="fb-rows">
                <div className="fb-row">
                  <span>عمر الحساب</span>
                  <span>{seller.account_age_days} يوم</span>
                </div>
                <div className="fb-row">
                  <span>عدد المنشورات</span>
                  <span>{seller.post_count}</span>
                </div>
                <div className="fb-row">
                  <span>المنصة</span>
                  <span>{seller.platform}</span>
                </div>
              </div>
            </div>

            <div className="results-trust-card">
              <TrustScore score={trust?.score} />
              <AiVerdict text={trust?.verdict_narrative} />
              <PrimaryButton fullWidth variant="green" onClick={handleSellerProfile}>
                <FiEye /> عرض الملف الكامل للبائع
              </PrimaryButton>
            </div>
          </>
        )}

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