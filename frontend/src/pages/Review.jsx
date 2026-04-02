import "./Review.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiCheckCircle,
  FiTrendingUp,
  FiPackage,
  FiStar,
  FiPhone,
  FiUser,
  FiLink,
} from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import FormInput from "../components/FormInput";

const CRITERIA = [
  {
    id: "match",
    label: "المنتج طابق الإعلان",
    icon: <FiCheckCircle size={16} />,
  },
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

  // Seller info
  const [sellerPhone, setSellerPhone] = useState("");
  const [sellerUsername, setSellerUsername] = useState("");
  const [sellerLink, setSellerLink] = useState("");

  // Review info
  const [rating, setRating] = useState(0);
  const [checked, setChecked] = useState({});
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  function toggleCheck(id) {
    setChecked((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  async function handleSubmit() {
    if (!user) {
      setError("⚠️ يجب تسجيل الدخول أولاً");
      navigate("/auth");
      return;
    }
    if (!sellerPhone && !sellerUsername && !sellerLink) {
      setError("⚠️ أدخل رقم الهاتف أو اسم المستخدم أو رابط الحساب");
      return;
    }
    if (!rating) {
      setError("⚠️ يرجى اختيار تقييم بالنجوم");
      return;
    }
    if (!description.trim()) {
      setError("⚠️ يرجى كتابة وصف واضح للتجربة");
      return;
    }

    setError("");
    setLoading(true);
    try {
      // Build seller identifier
      const sellerIdentifier = sellerLink || sellerUsername || sellerPhone;

      await thiqaApi.submitReview({
        profile_url: sellerIdentifier,
        stars: rating,
        description,
        tags: Object.keys(checked).filter((k) => checked[k]),
        contacts: {
          phone: sellerPhone,
          username: sellerUsername,
          profile_link: sellerLink,
        },
      });

      setSuccess(true);
      setTimeout(() => navigate("/"), 3000);
    } catch (e) {
      setError("⚠️ حدث خطأ أثناء إرسال المراجعة، حاول مرة أخرى");
    } finally {
      setLoading(false);
    }
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

        {/* Seller info */}

        <div className="review-field">
          <label>رابط الحساب</label>
          <FormInput
            type="text"
            placeholder="facebook.com/..."
            value={sellerLink}
            onChange={(e) => setSellerLink(e.target.value)}
            icon={<FiLink size={16} />}
          />
        </div>

        {/* Rating stars */}
        <div className="review-field">
          <label>
            تقييمك بالنجوم <span className="required">*</span>
          </label>
          <StarRating value={rating} onChange={setRating} />
        </div>

        {/* Criteria checkboxes */}
        <div className="review-field">
          <label>تقييم التجربة</label>
          <div className="criteria-list">
            {CRITERIA.map((c) => (
              <label
                key={c.id}
                className={`criteria-item ${checked[c.id] ? "checked" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={!!checked[c.id]}
                  onChange={() => toggleCheck(c.id)}
                  hidden
                />
                <span className="criteria-label">
                  {c.icon} {c.label}
                </span>
                <span
                  className={`criteria-check ${checked[c.id] ? "active" : ""}`}
                >
                  {checked[c.id] ? "✓" : ""}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Description */}
        <div className="review-field">
          <label>
            وصف تجربتك <span className="required">*</span>
          </label>
          <textarea
            placeholder="اشرح بالتفصيل ما حدث مع البائع، المنتج، والخدمة..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={5}
          />
        </div>

        {/* Error & success messages */}
        {error && <div className="review-error">{error}</div>}
        {success && (
          <div className="review-success">
            ✅ تم إرسال المراجعة بنجاح! شكراً.
          </div>
        )}

        <PrimaryButton fullWidth variant="green" onClick={handleSubmit}>
          {loading ? "جاري الإرسال..." : "إرسال المراجعة"}
        </PrimaryButton>
      </div>
    </main>
  );
}
