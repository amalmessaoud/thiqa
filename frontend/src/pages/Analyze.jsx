import "./Analyze.css";
import { useState } from "react";
import { FiImage, FiUpload } from "react-icons/fi";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";

export default function Analyze() {
  const [image, setImage] = useState(null);

  function handleImageChange(e) {
    if (e.target.files[0]) setImage(e.target.files[0]);
  }

  function handleAnalyze() {
    // TODO: connect to backend /api/analyze/image/
    alert("جاري التحليل...");
  }

  return (
    <main className="analyze-page" dir="rtl">
      {/* Header */}
      <div className="analyze-header">
        <div className="analyze-header-icon" style={{ background: "#f0fdf8", color: "#1D9E75" }}>
          <FiImage size={28} />
        </div>
        <h1>تحليل صور</h1>
        <p>ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة</p>
      </div>

      {/* Upload Card */}
      <div className="analyze-card">
        <div className="analyze-card-title">
          <FiUpload size={16} /> رفع الصورة
        </div>
        <UploadBox image={image} onChange={handleImageChange} />
        <PrimaryButton fullWidth onClick={handleAnalyze}>تحليل</PrimaryButton>
      </div>

      <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
    </main>
  );
}