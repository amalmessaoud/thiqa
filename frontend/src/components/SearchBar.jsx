import "./SearchBar.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FiSearch } from "react-icons/fi";

export default function SearchBar({ initialValue = "" }) {
  const [query, setQuery] = useState(initialValue);
  const navigate = useNavigate();

  function handleSearch() {
    if (query.trim()) navigate(`/results?q=${encodeURIComponent(query)}`);
  }

  return (
    <div className="search-card">
      <div className="search-box">
        <input
          className="search-input"
          type="text"
          placeholder="أدخل رابط الصفحة واحصل على تقييم من 0 إلى 100"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button className="search-btn" onClick={handleSearch}>
          <FiSearch /> بحث
        </button>
      </div>
      <p className="search-hint">مثال: <span>facebook.com/pagename</span></p>
    </div>
  );
}