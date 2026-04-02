import "./Home.css";
import { useNavigate } from "react-router-dom";
import { FiAlertTriangle, FiImage, FiStar } from "react-icons/fi";
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

      <section className="tools">
        <div className="tools-grid">
          <div className="tool-card" onClick={() => navigate("/report")}>
            <div className="tool-icon">
              <FiAlertTriangle size={22} />
            </div>
            <div className="tool-text">
              <h3>إبلاغ عن بائع</h3>
              <p>ساعد المجتمع بالإبلاغ عن البائعين النصابين</p>
            </div>
          </div>

          <div className="tool-card" onClick={() => navigate("/review")}>
            <div className="tool-icon">
              <FiStar size={22} />
            </div>
            <div className="tool-text">
              <h3>تقييم البائع</h3>
              <p>شارك تجربتك وقيّم البائع لمساعدة الآخرين</p>
            </div>
          </div>

          <div className="tool-card" onClick={() => navigate("/analyze")}>
            <div className="tool-icon">
              <FiImage size={22} />
            </div>
            <div className="tool-text">
              <h3>تحليل الصور</h3>
              <p>ارفع صورة منتج أو إعلان للكشف عن الصور المزيفة</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
