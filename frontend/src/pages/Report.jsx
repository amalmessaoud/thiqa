import "./Report.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiAlertTriangle, FiPhone, FiUser, FiLink, FiImage } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import PrimaryButton from "../components/PrimaryButton";
import FormInput from "../components/FormInput";

const SCAM_TYPES = [
  "لم تصلني البضاعة",
  "المنتج مزيف أو مختلف",
  "اخذ المال و لم يرد على الرسائل",
  "الحساب مزيف",
  "أخرى",
];

export default function Report() {
  const [phone, setPhone] = useState("");
  const [username, setUsername] = useState("");
  const [fbLink, setFbLink] = useState("");
  const [selectedTypes, setSelectedTypes] = useState([]);
  const [description, setDescription] = useState("");
  const [image, setImage] = useState(null);
  const { user } = useAuth();
  const navigate = useNavigate();

  function toggleType(type) {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  }

  function handleImageChange(e) {
    if (e.target.files[0]) setImage(e.target.files[0]);
  }

  function handleSubmit() {
    if (!user) { navigate("/auth"); return; }
    alert("تم إرسال التقرير!");
  }

  return (
    <main className="report-page" dir="rtl">
      <div className="report-header">
        <div className="report-header-icon"><FiAlertTriangle size={28} /></div>
        <h1>إبلاغ عن بائع</h1>
        <p>ساعد المجتمع بالإبلاغ عن البائعين النصابين</p>
      </div>

      <div className="report-warning">
        <span className="warning-label">ملاحظة:</span>
        <span> التقارير الكاذبة ستؤدي إلى حظر الحساب. تأكد من صحة المعلومات قبل الإرسال.</span>
      </div>

      <div className="report-section">
        <h2>معلومات البائع</h2>
        <p className="section-hint">أدخل أي معلومة تعرفها عن البائع (واحد على الأقل):</p>
        <div className="report-fields">
          <FormInput label="رقم الهاتف" type="tel" placeholder="0550123456"
            value={phone} onChange={(e) => setPhone(e.target.value)} icon={<FiPhone size={16} />} />
          <FormInput label="اسم المستخدم" type="text" placeholder="seller_dz@"
            value={username} onChange={(e) => setUsername(e.target.value)} icon={<FiUser size={16} />} />
          <FormInput label="رابط فيسبوك" type="text" placeholder="facebook.com/page.name"
            value={fbLink} onChange={(e) => setFbLink(e.target.value)} icon={<FiLink size={16} />} />
        </div>
      </div>

      <div className="report-section">
        <h2>نوع النصب</h2>
        <div className="scam-types">
          {SCAM_TYPES.map((type) => (
            <label key={type} className="scam-type-option">
              <input type="checkbox" checked={selectedTypes.includes(type)}
                onChange={() => toggleType(type)} />
              {type}
            </label>
          ))}
        </div>
      </div>

      <div className="report-section">
        <h2>وصف المشكلة <span className="required">*</span></h2>
        <textarea className="report-textarea"
          placeholder="اشرح ما حدث بالتفصيل... كيف تواصلت مع البائع، ماذا طلب، ماذا حدث، إلخ."
          value={description} onChange={(e) => setDescription(e.target.value)} rows={5} />
        <p className="section-hint">كلما كان الوصف أكثر تفصيلاً، كلما ساعدت أكثر في حماية الآخرين</p>
      </div>

      <div className="report-section">
        <h2>الدليل <span className="required">*</span></h2>
        <p className="section-hint">(يجب إرفاق صورة لمحادثة او البضاعة كدليل على ابلاغك)</p>
        <label className="upload-area">
          <input type="file" accept="image/*" onChange={handleImageChange} hidden />
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

      <div className="report-submit">
        <PrimaryButton fullWidth onClick={handleSubmit}>إرسال التقرير</PrimaryButton>
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