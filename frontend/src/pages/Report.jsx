import "./Report.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FiAlertTriangle,
  FiPhone,
  FiUser,
  FiLink,
  FiImage,
} from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import { thiqaApi } from "../api/thiqa";
import PrimaryButton from "../components/PrimaryButton";
import FormInput from "../components/FormInput";

const SCAM_TYPES = [
  { label: "لم تصلني البضاعة", value: "no_response" },
  { label: "المنتج مزيف أو مختلف", value: "fake_product" },
  { label: "اخذ المال و لم يرد على الرسائل", value: "advance_payment" },
  { label: "الحساب مزيف", value: "ghost_seller" },
  { label: "أخرى", value: "other" },
];

export default function Report() {
  const [platform, setPlatform] = useState("facebook");
  const [phone, setPhone] = useState("");
  const [username, setUsername] = useState("");
  const [fbLink, setFbLink] = useState("");
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [description, setDescription] = useState("");
  const [image, setImage] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState([]);
  function toggleType(type) {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  }

  function handleImageChange(e) {
    if (e.target.files[0]) setImage(e.target.files[0]);
  }

  async function handleSubmit() {
    if (!user) {
      setError("⚠️ يجب تسجيل الدخول أولاً");
      navigate("/auth");
      return;
    }

    if (!fbLink && !phone && !username) {
      setError("⚠️ أدخل رقم الهاتف أو اسم المستخدم أو رابط الحساب");
      return;
    }

    if (selectedTypes.length === 0) {
      setError("⚠️ اختر نوع النصب على الأقل");
      return;
    }

    if (!description.trim()) {
      setError("⚠️ يرجى كتابة وصف واضح للمشكلة");
      return;
    }

    if (!image) {
      setError("⚠️ يجب إرفاق صورة كدليل");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await thiqaApi.submitReport({
        seller_url: fbLink || username || phone,
        platform: platform,
        scam_type: selectedTypes.join(","),
        description,
        screenshot: image,
      });

      setSuccess(true);

      // ✅ Capture top 3 recommendations
      if (response?.recommendations?.length > 0) {
        setRecommendations(response.recommendations.slice(0, 3));
      }
    } catch (e) {
      if (e.response?.status === 400)
        setError("⚠️ البيانات غير صحيحة، تحقق منها");
      else if (e.response?.status === 500)
        setError("⚠️ خطأ في الخادم، حاول لاحقاً");
      else setError("⚠️ حدث خطأ غير متوقع");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="report-page" dir="rtl">
      <div className="report-header">
        <div className="report-header-icon">
          <FiAlertTriangle size={28} />
        </div>
        <h1>إبلاغ عن بائع</h1>
        <p>ساعد المجتمع بالإبلاغ عن البائعين النصابين</p>
      </div>

      <div className="report-warning">
        <span className="warning-label">ملاحظة:</span>
        <span>
          {" "}
          التقارير الكاذبة ستؤدي إلى حظر الحساب. تأكد من صحة المعلومات قبل
          الإرسال.
        </span>
      </div>

      <div className="report-section">
        <h2>معلومات البائع</h2>
        <p className="section-hint">
          أدخل أي معلومة تعرفها عن البائع (واحد على الأقل):
        </p>
        <div className="platform-select">
          <label>المنصة</label>
          <select
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="facebook">Facebook</option>
            <option value="instagram">Instagram</option>
            <option value="tiktok">TikTok</option>
          </select>
        </div>
        <div className="report-fields">
          <FormInput
            label="رقم الهاتف"
            type="tel"
            placeholder="0550123456"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            icon={<FiPhone size={16} />}
          />
          <FormInput
            label="اسم المستخدم"
            type="text"
            placeholder="seller_dz@"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            icon={<FiUser size={16} />}
          />
          <FormInput
            label={`رابط ${platform}`}
            type="text"
            placeholder={`${platform}.com/...`}
            value={fbLink}
            onChange={(e) => setFbLink(e.target.value)}
            icon={<FiLink size={16} />}
          />
        </div>
      </div>
      <div className="report-top"></div>
      <div className="report-section">
        <h2>نوع النصب</h2>
        <div className="scam-types">
          {SCAM_TYPES.map((type) => (
            <label key={type.value} className="scam-type-option">
              <input
                type="checkbox"
                checked={selectedTypes.includes(type.value)}
                onChange={() => toggleType(type.value)}
              />
              {type.label}
            </label>
          ))}
        </div>
      </div>
      {/* ===== Recommendations Popup ===== */}
      {recommendations.length > 0 && (
        <div className="recommendation-modal">
          <div className="recommendation-content">
            <h2>توصيات مشابهة</h2>
            <p>قد تكون هذه الحسابات مرتبطة ببلاغات مشابهة:</p>
            <ul>
              {recommendations.map((rec) => (
                <li key={rec.id}>
                  <a
                    href={rec.profile_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {rec.display_name || rec.profile_url} ({rec.platform})
                  </a>{" "}
                  - {rec.category}
                </li>
              ))}
            </ul>
            <PrimaryButton onClick={() => setRecommendations([])}>
              إغلاق
            </PrimaryButton>
          </div>
        </div>
      )}

      <div className="report-section">
        <h2>
          وصف المشكلة <span className="required">*</span>
        </h2>
        <textarea
          className="report-textarea"
          placeholder="اشرح ما حدث بالتفصيل... كيف تواصلت مع البائع، ماذا طلب، ماذا حدث، إلخ."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
        />
        <p className="section-hint">
          كلما كان الوصف أكثر تفصيلاً، كلما ساعدت أكثر في حماية الآخرين
        </p>
      </div>

      <div className="report-section">
        <h2>
          الدليل <span className="required">*</span>
        </h2>
        <p className="section-hint">
          (يجب إرفاق صورة لمحادثة او البضاعة كدليل على ابلاغك)
        </p>
        <label className="upload-area">
          <input
            type="file"
            accept="image/*"
            onChange={handleImageChange}
            hidden
          />
          {image ? (
            <span className="upload-filename">✅ {image.name}</span>
          ) : (
            <div className="upload-placeholder">
              <FiImage size={32} />
              <span>اضغط لرفع صورة</span>
            </div>
          )}
        </label>
      </div>

      {error && <div className="report-error">{error}</div>}
      {success && (
        <div className="report-success">
          ✅ تم إرسال التقرير بنجاح! شكراً على مساهمتك.
        </div>
      )}

      <div className="report-submit">
        <PrimaryButton fullWidth onClick={handleSubmit}>
          {loading ? "جاري الإرسال..." : "إرسال التقرير"}
        </PrimaryButton>
      </div>

      <div className="report-howto">
        <h3>كيف نستخدم تقريرك؟</h3>
        <ul>
          <li>✓ نربط جميع المعلومات تلقائياً (رقم، اسم مستخدم، رابط)</li>
          <li>✓ نخفض نقاط الثقة للبائع المبلغ عنه</li>
          <li>✓ تعرض تقاريرك للآخرين عند البحث عن هذا البائع</li>
          <li>✓ كلما زادت التقارير، انخفضت نقاط الثقة أكثر</li>
        </ul>
      </div>
    </main>
  );
}
