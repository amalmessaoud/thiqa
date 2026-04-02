import "./Analyze.css";
import "./TextAnalyze.css";
import { useState } from "react";
import { FiImage, FiUpload, FiSearch, FiFileText } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";
import AiVerdict from "../components/AiVerdict";

// ─── Image Analysis Tab ───────────────────────────────────────────────────────
function ImageTab() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function handleImageChange(e) {
    if (e.target.files.length > 0) {
      setImages(e.target.files);
      setResult(null);
      setError("");
    }
  }

  async function handleAnalyze() {
    if (images.length === 0) {
      setError("يرجى رفع صورة أولاً");
      return;
    }
    setError("");
    setLoading(true);
    setResult(null);
    try {
      const data = await thiqaApi.analyzeImage(images[0]);
      setResult(data);
    } catch (e) {
      console.error(e);
      setError("حدث خطأ أثناء التحليل، حاول مرة أخرى");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="analyze-card-title">
        <FiUpload size={16} /> رفع الصورة
      </div>
      <UploadBox images={images} onChange={handleImageChange} />
      {error && <div className="analyze-error">{error}</div>}
      <PrimaryButton fullWidth onClick={handleAnalyze}>
        {loading ? "جاري التحليل..." : "تحليل"}
      </PrimaryButton>

      {result ? (
        <div className="analyze-tab-results">
          <div className="analyze-verdict" style={{ marginBottom: "0" }}>
            {result.is_ai_generated
              ? `⚠️ يُشير التحليل إلى أن الصورة محتملة أن تكون منشأة بواسطة الذكاء الاصطناعي بنسبة ثقة ${result.confidence * 100}%`
              : "✅ الصورة تبدو أصلية"}
          </div>
          {result.verdict_arabic && (
            <div className="analyze-verdict-text">{result.verdict_arabic}</div>
          )}
          {result.reasons && result.reasons.length > 0 && (
            <ul className="analyze-list">
              {result.reasons.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          )}
          <div className="analyze-verdict-text">
            {result.safe_to_trust
              ? "✅ الصورة آمنة للاعتماد"
              : "⚠️ الصورة قد لا تكون آمنة للاعتماد"}
          </div>
        </div>
      ) : (
        <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
      )}
    </>
  );
}

// ─── Text / Screenshot Analysis Tab ──────────────────────────────────────────
function TextTab() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function handleImageChange(e) {
    if (e.target.files.length > 0) {
      setImages(Array.from(e.target.files));
      setResult(null);
      setError("");
    }
  }

  async function handleAnalyze() {
    if (images.length === 0) {
      setError("يرجى رفع صورة واحدة على الأقل");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const data = await thiqaApi.analyzeScreenshot(images);
      setResult(data);
    } catch (e) {
      setError("حدث خطأ أثناء التحليل، حاول مرة أخرى");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="analyze-card-title">
        <FiFileText size={16} /> صور النصوص أو المحادثات
      </div>
      <UploadBox
        images={images}
        onChange={handleImageChange}
        multiple={true}
        hint="يمكنك رفع أكثر من صورة محادثة من واتساب، إنستغرام، أو أي منصة"
      />
      <div className="how-it-works">
        <p>
          <strong>كيف يعمل:</strong>
        </p>
        <p>١. استخراج النص من جميع الصور المرفوعة</p>
        <p>٢. تحليل النصوص بحثاً عن أنماط النصب</p>
      </div>
      {error && <div className="analyze-error">{error}</div>}
      <PrimaryButton fullWidth onClick={handleAnalyze}>
        {loading ? "جاري التحليل..." : "تحليل جميع الصور"}
      </PrimaryButton>

      {result ? (
        <div className="analyze-tab-results">
          {result.extracted_text && (
            <div className="analyze-extracted">
              <p className="analyze-extracted-label">النص المستخرج:</p>
              <p className="analyze-extracted-text">{result.extracted_text}</p>
            </div>
          )}
          <div className="analyze-info">
            <p>✅ الثقة: {(result.confidence * 100).toFixed(1)}%</p>
            <p>📝 عدد الكلمات: {result.word_count}</p>
            <p>🖼️ عدد الصور المعالجة: {result.images_processed}</p>
            <p>⚠️ عدد الصور الفاشلة: {result.images_failed}</p>
          </div>
          {result.analysis && (
            <>
              <AiVerdict text={result.analysis.verdict_darija} />
              <div
                className={`analyze-verdict ${result.analysis.safe_to_proceed ? "real" : "fake"}`}
              >
                {result.analysis.safe_to_proceed
                  ? "✅ المحادثة تبدو طبيعية"
                  : "⚠️ محادثة مشبوهة - احذر من هذا البائع"}
              </div>
              {result.analysis.scam_type && (
                <p className="analyze-verdict-text">
                  نوع النصب: {result.analysis.scam_type}
                </p>
              )}
              {result.analysis.red_flags.length > 0 && (
                <div className="analyze-red-flags">
                  <p>⚠️ علامات تحذيرية:</p>
                  <ul className="analyze-list">
                    {result.analysis.red_flags.map((flag, i) => (
                      <li key={i}>{flag}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <ResultsPlaceholder message='ارفع صورة واحدة على الأقل واضغط "تحليل جميع الصور" لرؤية النتائج' />
      )}
    </>
  );
}

// ─── Tab config ───────────────────────────────────────────────────────────────
const TABS = [
  {
    key: "image",
    label: "تحليل صور",
    icon: <FiImage size={17} />,
    headerIcon: { bg: "#f0fdf8", color: "#1D9E75", el: <FiImage size={28} /> },
    title: "تحليل الصور",
    subtitle: "ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة",
    component: <ImageTab />,
  },
  {
    key: "text",
    label: "تحليل النصوص",
    icon: <FiSearch size={17} />,
    headerIcon: { bg: "#f0f4ff", color: "#122040", el: <FiSearch size={28} /> },
    title: "تحليل النصوص والرسائل",
    subtitle: "ارفع صورة أو أكثر لمحادثة أو إعلان للكشف عن البائعين المزيفين",
    component: <TextTab />,
  },
];

// ─── Combined Page ────────────────────────────────────────────────────────────
export default function Analyze() {
  const [activeTab, setActiveTab] = useState("image");
  const tab = TABS.find((t) => t.key === activeTab);

  return (
    <main className="analyze-page" dir="rtl">
      {/* Header */}
      <div className="analyze-header">
        <div
          className="analyze-header-icon"
          style={{ background: tab.headerIcon.bg, color: tab.headerIcon.color }}
        >
          {tab.headerIcon.el}
        </div>
        <h1>{tab.title}</h1>
        <p>{tab.subtitle}</p>
      </div>

      {/* Single card containing tabs + content */}
      <div className="analyze-card">
        <div className="analyze-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={`analyze-tab-btn${activeTab === t.key ? " active" : ""}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        {tab.component}
      </div>
    </main>
  );
}
