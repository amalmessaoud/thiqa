import "./Analyze.css";
import { useState } from "react";
import { FiImage, FiUpload } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";
import TrustScore from "../components/TrustScore";
import AiVerdict from "../components/AiVerdict";

export default function Analyze() {
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  function handleImageChange(e) {
    if (e.target.files[0]) {
      setImage(e.target.files[0]);
      setResult(null);
      setError("");
    }
  }

  async function handleAnalyze() {
    if (!image) { setError("يرجى رفع صورة أولاً"); return; }
    setError("");
    setLoading(true);
    try {
      const data = await thiqaApi.analyzeImage(image);
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
        <div className="analyze-header-icon" style={{ background: "#f0fdf8", color: "#1D9E75" }}>
          <FiImage size={28} />
        </div>
        <h1>تحليل صور</h1>
        <p>ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة</p>
      </div>

      <div className="analyze-card">
        <div className="analyze-card-title">
          <FiUpload size={16} /> رفع الصورة
        </div>
        <UploadBox image={image} onChange={handleImageChange} />
        {error && <div className="analyze-error">{error}</div>}
        <PrimaryButton fullWidth onClick={handleAnalyze}>
          {loading ? "جاري التحليل..." : "تحليل"}
        </PrimaryButton>
      </div>

      {/* Results */}
      {result ? (
        <div className="analyze-results">
          {result.trust_score && <TrustScore score={result.trust_score.score} />}
          {result.verdict_narrative && <AiVerdict text={result.verdict_narrative} />}
          {result.is_fake !== undefined && (
            <div className={`analyze-verdict ${result.is_fake ? "fake" : "real"}`}>
              {result.is_fake ? "⚠️ الصورة مشبوهة أو مزيفة" : "✅ الصورة تبدو أصلية"}
            </div>
          )}
          {result.verdict && (
            <div className="analyze-verdict-text">{result.verdict}</div>
          )}
        </div>
      ) : (
        !loading && <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
      )}
    </main>
  );
}