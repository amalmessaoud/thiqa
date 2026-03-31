import "./Auth.css";
import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { FiEye, FiEyeOff } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import PrimaryButton from "../components/PrimaryButton";
import logo from "../assets/logo.svg";

export default function Auth() {
  const location = useLocation();
  const [isLogin, setIsLogin] = useState(!location.state?.register);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();
  const navigate = useNavigate();

  async function handleLogin() {
    if (!email || !password) { setError("يرجى ملء جميع الحقول"); return; }
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (e) {
      setError("البريد الإلكتروني أو كلمة المرور غير صحيحة");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    if (!firstName || !lastName || !email || !password) {
      setError("يرجى ملء جميع الحقول"); return;
    }
    if (password !== confirmPassword) {
      setError("كلمتا المرور غير متطابقتين"); return;
    }
    setError("");
    setLoading(true);
    try {
      await register(firstName, lastName, email, password);
      navigate("/");
    } catch (e) {
      setError("حدث خطأ أثناء إنشاء الحساب، حاول مرة أخرى");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-logo">
        <img src={logo} alt="Thiqa" />
        <p>تحقق من أي بائع قبل ما تسلك !!</p>
      </div>

      <div className="auth-card">
        {error && <div className="auth-error">{error}</div>}

        {isLogin ? (
          <div className="auth-form" dir="rtl">
            <div className="form-group">
              <label>البريد الإلكتروني</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>كلمة المرور</label>
              <div className="input-icon">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleLogin()}
                />
                <button onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <div className="form-row">
              <span className="forgot">نسيت كلمة المرور؟</span>
              <label className="remember">
                <input type="checkbox" /> تذكرني
              </label>
            </div>
            <PrimaryButton fullWidth variant="green" onClick={handleLogin}>
              {loading ? "جاري التحميل..." : "تسجيل الدخول"}
            </PrimaryButton>
            <p className="auth-switch">
              ليس لديك حساب؟{" "}
              <span onClick={() => { setIsLogin(false); setError(""); }}>إنشاء حساب</span>
            </p>
          </div>
        ) : (
          <div className="auth-form" dir="rtl">
            <div className="form-row-two">
              <div className="form-group">
                <label>اسم العائلة</label>
                <input
                  type="text"
                  placeholder="محمد"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>الاسم الأول</label>
                <input
                  type="text"
                  placeholder="أحمد"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
            </div>
            <div className="form-group">
              <label>البريد الإلكتروني</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>كلمة المرور</label>
              <div className="input-icon">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <div className="form-group">
              <label>تأكيد كلمة المرور</label>
              <div className="input-icon">
                <input
                  type={showConfirm ? "text" : "password"}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRegister()}
                />
                <button onClick={() => setShowConfirm(!showConfirm)}>
                  {showConfirm ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <PrimaryButton fullWidth variant="green" onClick={handleRegister}>
              {loading ? "جاري التحميل..." : "إنشاء حساب"}
            </PrimaryButton>
            <p className="auth-switch">
              لديك حساب بالفعل؟{" "}
              <span onClick={() => { setIsLogin(true); setError(""); }}>تسجيل الدخول</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}