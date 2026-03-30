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
  const { login } = useAuth();
  const navigate = useNavigate();

  function handleLogin() {
    login({ name: "مستخدم" });
    navigate("/");
  }

  function handleRegister() {
    login({ name: "مستخدم" });
    navigate("/");
  }

  return (
    <div className="auth-page">
      <div className="auth-logo">
        <img src={logo} alt="Thiqa" />
        <p>تحقق من أي بائع قبل ما تسلك !!</p>
      </div>

      <div className="auth-card">
        {isLogin ? (
          <div className="auth-form" dir="rtl">
            <div className="form-group">
              <label>البريد الإلكتروني</label>
              <input type="email" placeholder="you@example.com" />
            </div>
            <div className="form-group">
              <label>كلمة المرور</label>
              <div className="input-icon">
                <input type={showPassword ? "text" : "password"} placeholder="••••••••" />
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
              تسجيل الدخول
            </PrimaryButton>
            <p className="auth-switch">
              ليس لديك حساب؟{" "}
              <span onClick={() => setIsLogin(false)}>إنشاء حساب</span>
            </p>
          </div>
        ) : (
          <div className="auth-form" dir="rtl">
            <div className="form-row-two">
              <div className="form-group">
                <label>اسم العائلة</label>
                <input type="text" placeholder="محمد" />
              </div>
              <div className="form-group">
                <label>الاسم الأول</label>
                <input type="text" placeholder="أحمد" />
              </div>
            </div>
            <div className="form-group">
              <label>البريد الإلكتروني</label>
              <input type="email" placeholder="you@example.com" />
            </div>
            <div className="form-group">
              <label>كلمة المرور</label>
              <div className="input-icon">
                <input type={showPassword ? "text" : "password"} placeholder="••••••••" />
                <button onClick={() => setShowPassword(!showPassword)}>
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <div className="form-group">
              <label>تأكيد كلمة المرور</label>
              <div className="input-icon">
                <input type={showConfirm ? "text" : "password"} placeholder="••••••••" />
                <button onClick={() => setShowConfirm(!showConfirm)}>
                  {showConfirm ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <PrimaryButton fullWidth variant="green" onClick={handleRegister}>
              إنشاء حساب
            </PrimaryButton>
            <p className="auth-switch">
              لديك حساب بالفعل؟{" "}
              <span onClick={() => setIsLogin(true)}>تسجيل الدخول</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}