import "./NavBar.css";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { FiUser, FiMenu, FiX, FiHome, FiImage, FiFileText, FiAlertTriangle, FiSlash } from "react-icons/fi";
import { useAuth } from "../context/AuthContext";
import logo from "../assets/logo.svg";

const NAV_LINKS = [
  { path: "/", label: "الصفحة الرئيسية", icon: <FiHome size={16} /> },
  { path: "/analyze", label: "محلل الصور", icon: <FiImage size={16} /> },
  { path: "/text-analyze", label: "محلل النصوص والرسائل", icon: <FiFileText size={16} /> },
  { path: "/report", label: "الإبلاغ عن البائعين", icon: <FiAlertTriangle size={16} /> },
  { path: "/blacklist", label: "القائمة السوداء", icon: <FiSlash size={16} /> },
];

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);

  const isActive = (path) =>
    location.pathname === path ? "nav-link active" : "nav-link";

  const close = () => setOpen(false);

  function handleLogout() {
    logout();
    navigate("/");
    close();
  }

  return (
    <>
      <nav className="navbar" dir="rtl">
        <div className="navbar-logo">
          <Link to="/" onClick={close}>
            <img src={logo} alt="Thiqa" />
          </Link>
        </div>

        {/* Desktop links */}
        <ul className="navbar-links">
          {NAV_LINKS.map((l) => (
            <li key={l.path}>
              <Link to={l.path} className={isActive(l.path)}>{l.label}</Link>
            </li>
          ))}
        </ul>

        {/* Desktop actions */}
        <div className="navbar-actions">
          {user ? (
            <>
              <button className="btn-profile" onClick={() => navigate("/profile")}>
                <FiUser size={15} /> الملف الشخصي
              </button>
              <button className="btn-logout" onClick={handleLogout}>
                تسجيل الخروج
              </button>
            </>
          ) : (
            <>
              <Link to="/auth" className="btn-login">تسجيل الدخول</Link>
              <Link to="/auth" state={{ register: true }} className="btn-register">إنشاء حساب</Link>
            </>
          )}
        </div>

        {/* Hamburger */}
        <button className="hamburger" onClick={() => setOpen(true)} aria-label="open menu">
          <FiMenu size={26} />
        </button>
      </nav>

      {/* Overlay */}
      <div className={`sidebar-overlay${open ? " visible" : ""}`} onClick={close} />

      {/* Sidebar */}
      <aside className={`sidebar${open ? " open" : ""}`} dir="rtl">
        <div className="sidebar-top">
          <img src={logo} alt="Thiqa" className="sidebar-logo" />
          <button className="sidebar-close" onClick={close} aria-label="close menu">
            <FiX size={24} />
          </button>
        </div>

        <ul className="sidebar-nav">
          {NAV_LINKS.map((l) => (
            <li key={l.path}>
              <Link to={l.path} className={isActive(l.path)} onClick={close}>
                <span className="sidebar-icon">{l.icon}</span>
                {l.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          {user ? (
            <>
              <button
                className="btn-profile full"
                onClick={() => { navigate("/profile"); close(); }}
              >
                <FiUser size={15} /> الملف الشخصي
              </button>
              <button className="btn-logout full" onClick={handleLogout}>
                تسجيل الخروج
              </button>
            </>
          ) : (
            <>
              <Link to="/auth" className="btn-login full" onClick={close}>
                تسجيل الدخول
              </Link>
              <Link to="/auth" state={{ register: true }} className="btn-register full" onClick={close}>
                إنشاء حساب
              </Link>
            </>
          )}
        </div>
      </aside>
    </>
  );
}