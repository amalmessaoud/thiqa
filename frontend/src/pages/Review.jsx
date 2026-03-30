import "./Review.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiCheckCircle, FiTrendingUp, FiPackage, FiStar } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import PrimaryButton from "../components/PrimaryButton";
import FormInput from "../components/FormInput";

const CRITERIA = [
  { id: "match", label: "المنتج طابق الإعلان", icon: <FiCheckCircle size={16} /> },
  { id: "fast", label: "البائع رد بسرعة", icon: <FiTrendingUp size={16} /> },
  { id: "received", label: "استلمت البضاعة", icon: <FiPackage size={16} /> },
  { id: "again", label: "أشتري منه مرة أخرى", icon: <FiStar size={16} /> },
];

function StarRating({ value, onChange }) {
  const [hovered, setHovered] = useState(0);
  return (
    <div className="star-rating">
      {[1, 2, 3, 4, 5].map((s) => (
        <button
          key={s}
          type="button"
          className={`star-btn ${s <= (hovered || value) ? "filled" : ""}`}
          onClick={() => onChange(s)}
          onMouseEnter={() => setHovered(s)}
          onMouseLeave={() => setHovered(0)}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export default function Review() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [seller, setSeller] = useState("");
  const [rating, setRating] = useState(0);
  const [checked, setChecked] = useState({});

  function toggleCheck(id) {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function handleSubmit() {
    if (!user) { navigate("/auth"); return; }
    alert("تم إرسال المراجعة!");
    navigate("/");
  }

  return (
    <main className="review-page" dir="rtl">
      <div className="review-header">
        <div className="review-header-icon">
          <FiStar size={28} />
        </div>
        <h1>تقييم بعد الشراء</h1>
        <p>ساعد الآخرين بمشاركة تجربتك مع البائع</p>
      </div>

      <div className="review-card">
        <h3>إضافة مراجعة جديدة</h3>

        <div className="review-field">
          <label>معلومات البائع <span className="required">*</span></label>
          <FormInput
            type="text"
            placeholder="رقم الهاتف، اسم المستخدم، أو رابط الصفحة"
            value={seller}
            onChange={(e) => setSeller(e.target.value)}
          />
        </div>

        <div className="review-field">
          <label>تقييمك بالنجوم <span className="required">*</span></label>
          <StarRating value={rating} onChange={setRating} />
        </div>

        <div className="review-field">
          <label>تقييم التجربة</label>
          <div className="criteria-list">
            {CRITERIA.map((c) => (
              <label key={c.id} className={`criteria-item ${checked[c.id] ? "checked" : ""}`}>
                <input
                  type="checkbox"
                  checked={!!checked[c.id]}
                  onChange={() => toggleCheck(c.id)}
                  hidden
                />
                <span className="criteria-label">{c.icon} {c.label}</span>
                <span className={`criteria-check ${checked[c.id] ? "active" : ""}`}>
                  {checked[c.id] ? "✓" : ""}
                </span>
              </label>
            ))}
          </div>
        </div>

        <PrimaryButton fullWidth variant="green" onClick={handleSubmit}>
          إرسال المراجعة
        </PrimaryButton>
      </div>
    </main>
  );
}