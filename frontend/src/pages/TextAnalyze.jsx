import "./Analyze.css";
import "./TextAnalyze.css";
import { useState } from "react";
import { FiSearch, FiFileText } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";
import AiVerdict from "../components/AiVerdict";

export default function TextAnalyze() {
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
    if (images.length === 0) { setError("يرجى رفع صورة أولاً"); return; }
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
    <main className="analyze-page" dir="rtl">
      <div className="analyze-header">
        <div className="analyze-header-icon" style={{ background: "#f0f4ff", color: "#122040" }}>
          <FiSearch size={28} />
        </div>
        <h1>تحليل النصوص والرسائل</h1>
        <p>ارفع صورة لمحادثة أو اعلان للكشف عن البائعين المزيفين</p>
      </div>

      <div className="analyze-card">
        <div className="analyze-card-title">
          <FiFileText size={16} /> صورة النص أو المحادثة
        </div>
        <UploadBox
          images={images}
          onChange={handleImageChange}
          hint="صورة محادثة من واتساب، إنستغرام، أو أي منصة"
        />
        <div className="how-it-works">
          <p><strong>كيف يعمل:</strong></p>
          <p>١. استخراج النص من الصورة</p>
          <p>٢. تحليل النص بحثاً عن أنماط النصب</p>
        </div>
        {error && <div className="analyze-error">{error}</div>}
        <PrimaryButton fullWidth onClick={handleAnalyze}>
          {loading ? "جاري التحليل..." : "تحليل"}
        </PrimaryButton>
      </div>

      {result ? (
        <div className="analyze-results">
          {result.extracted_text && (
            <div className="analyze-extracted">
              <p className="analyze-extracted-label">النص المستخرج:</p>
              <p className="analyze-extracted-text">{result.extracted_text}</p>
            </div>
          )}
          {result.verdict_narrative && <AiVerdict text={result.verdict_narrative} />}
          {result.is_scam !== undefined && (
            <div className={`analyze-verdict ${result.is_scam ? "fake" : "real"}`}>
              {result.is_scam ? "⚠️ محادثة مشبوهة - احذر من هذا البائع" : "✅ المحادثة تبدو طبيعية"}
            </div>
          )}
        </div>
      ) : (
        !loading && <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
      )}
    </main>
  );
}