import "./Analyze.css";
import "./TextAnalyze.css";
import { useState } from "react";
import { FiSearch, FiFileText } from "react-icons/fi";
import PrimaryButton from "../components/PrimaryButton";
import UploadBox from "../components/UploadBox";
import ResultsPlaceholder from "../components/ResultsPlaceholder";

export default function TextAnalyze() {
  const [image, setImage] = useState(null);

  function handleImageChange(e) {
    if (e.target.files[0]) setImage(e.target.files[0]);
  }

  function handleAnalyze() {
    alert("جاري التحليل...");
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
          image={image}
          onChange={handleImageChange}
          hint="صورة محادثة من واتساب، إنستغرام، أو أي منصة"
        />
        <div className="how-it-works">
          <p><strong>كيف يعمل:</strong></p>
          <p>١. استخراج النص من الصورة</p>
          <p>٢. تحليل النص بحثاً عن أنماط النصب</p>
        </div>
        <PrimaryButton fullWidth onClick={handleAnalyze}>تحليل</PrimaryButton>
      </div>

      <ResultsPlaceholder message='ارفع صورة واضغط "تحليل" لرؤية النتائج' />
    </main>
  );
}