import "./Analyze.css";
import { useState } from "react";
import { FiImage, FiUpload } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";

export default function Analyze() {
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
      const data = await thiqaApi.analyzeImage(images[0]); // file under "image"
      setResult(data);
    } catch (e) {
      console.error(e);
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
          style={{ background: "#f0fdf8", color: "#1D9E75" }}
        >
          <FiImage size={28} />
        </div>
        <h1>تحليل صور</h1>
        <p>ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة</p>
      </div>

      <div className="analyze-card">
        <div className="analyze-card-title">
          <FiUpload size={16} /> رفع الصورة
        </div>
        <UploadBox images={images} onChange={handleImageChange} />
        {error && <div className="analyze-error">{error}</div>}
        <PrimaryButton fullWidth onClick={handleAnalyze}>
          {loading ? "جاري التحليل..." : "تحليل"}
        </PrimaryButton>
      </div>

      {result ? (
        <div className="analyze-results">
          <h2 style={{ marginTop: "1rem" }}>نتائج التحليل</h2>

          <div className="analyze-verdict" style={{ marginBottom: "1rem" }}>
            {result.is_ai_generated
              ? `⚠️ يُشير التحليل إلى أن الصورة محتملة أن تكون منشأة بواسطة الذكاء الاصطناعي بنسبة ثقة ${result.confidence * 100}%`
              : "✅ الصورة تبدو أصلية"}
          </div>

          {result.verdict_arabic && (
            <div className="analyze-verdict-text">{result.verdict_arabic}</div>
          )}

          {result.reasons && result.reasons.length > 0 && (
            <ul style={{ paddingInlineStart: "1.5rem", marginTop: "0.5rem" }}>
              {result.reasons.map((r, idx) => (
                <li key={idx}>{r}</li>
              ))}
            </ul>
          )}

          <div style={{ marginTop: "0.5rem" }}>
            {result.safe_to_trust
              ? "الصورة آمنة للاعتماد"
              : "⚠️ الصورة قد لا تكون آمنة للاعتماد"}
          </div>
        </div>
      ) : (
        !loading && (
          <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
        )
      )}
    </main>
  );
}
