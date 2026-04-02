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

  // Explicitly support multiple screenshots
  function handleImageChange(e) {
    if (e.target.files.length > 0) {
      setImages(Array.from(e.target.files)); // make sure it's an array
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
      // thiqaApi.analyzeScreenshot accepts multiple files
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
        <div
          className="analyze-header-icon"
          style={{ background: "#f0f4ff", color: "#122040" }}
        >
          <FiSearch size={28} />
        </div>
        <h1>تحليل النصوص والرسائل</h1>
        <p>ارفع صورة أو أكثر لمحادثة أو إعلان للكشف عن البائعين المزيفين</p>
      </div>

      <div className="analyze-card">
        <div className="analyze-card-title">
          <FiFileText size={16} /> صور النصوص أو المحادثات
        </div>
        <UploadBox
          images={images}
          onChange={handleImageChange}
          multiple={true} // explicitly allow multiple uploads
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
      </div>

      {result ? (
        <div className="analyze-results">
          <h2>نتائج التحليل</h2>

          {/* Extracted Text */}
          {result.extracted_text && (
            <div className="analyze-extracted">
              <p className="analyze-extracted-label">النص المستخرج:</p>
              <p className="analyze-extracted-text">{result.extracted_text}</p>
            </div>
          )}

          {/* General Info */}
          <div className="analyze-info">
            <p>✅ الثقة: {(result.confidence * 100).toFixed(1)}%</p>
            <p>📝 عدد الكلمات: {result.word_count}</p>
            <p>🖼️ عدد الصور المعالجة: {result.images_processed}</p>
            <p>⚠️ عدد الصور الفاشلة: {result.images_failed}</p>
          </div>

          {/* AI Verdict */}
          {result.analysis && (
            <>
              <AiVerdict text={result.analysis.verdict_darija} />

              <div
                className={`analyze-verdict ${
                  result.analysis.safe_to_proceed ? "real" : "fake"
                }`}
              >
                {result.analysis.safe_to_proceed
                  ? "✅ المحادثة تبدو طبيعية"
                  : "⚠️ محادثة مشبوهة - احذر من هذا البائع"}
              </div>

              {/* Scam type */}
              {result.analysis.scam_type && (
                <p>نوع النصب: {result.analysis.scam_type}</p>
              )}

              {/* Red Flags */}
              {result.analysis.red_flags.length > 0 && (
                <div className="analyze-red-flags">
                  <p>⚠️ علامات تحذيرية:</p>
                  <ul>
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
        !loading && (
          <ResultsPlaceholder message='ارفع صورة واحدة على الأقل واضغط "تحليل جميع الصور" لرؤية النتائج' />
        )
      )}
    </main>
  );
}
