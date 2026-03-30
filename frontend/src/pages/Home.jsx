import "./Home.css";
import { useNavigate } from "react-router-dom";
import { FiAlertTriangle, FiImage, FiFileText } from "react-icons/fi";
import SearchBar from "../components/SearchBar";
import logo from "../assets/logo.svg";

export default function Home() {
  const navigate = useNavigate();

  return (
    <main className="home">
      <section className="hero">
        <img src={logo} alt="Thiqa" className="hero-logo" />
        <p className="hero-subtitle">تحقق من أي بائع قبل ما تسلك !!</p>
        <SearchBar />
      </section>

      <section className="report-card" onClick={() => navigate("/report")}>
        <div className="report-icon"><FiAlertTriangle size={24} /></div>
        <div className="report-text">
          <h3>إبلاغ عن بائع</h3>
          <p>ساعد المجتمع بالإبلاغ عن البائعين النصابين</p>
        </div>
      </section>

      <section className="tools">
        <h2>أدوات أخرى</h2>
        <div className="tools-grid">
          <div className="tool-card" onClick={() => navigate("/analyze")}>
            <div className="tool-icon"><FiImage size={22} /></div>
            <div className="tool-text">
              <h3>تحليل الصور</h3>
              <p>ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة</p>
            </div>
          </div>
          <div className="tool-card" onClick={() => navigate("/text-analyze")}>
            <div className="tool-icon"><FiFileText size={22} /></div>
            <div className="tool-text">
              <h3>تحليل النصوص</h3>
              <p>ارفع صورة لمحادثة أو اعلان للكشف عن البائعين المزيفين</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}