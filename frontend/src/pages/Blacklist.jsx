import "./Blacklist.css";
import { useState, useEffect, useCallback } from "react";
import { FiAlertTriangle, FiSearch, FiFilter, FiChevronLeft, FiChevronRight } from "react-icons/fi";
import { thiqaApi } from "../api/thiqa";
import BlacklistCard from "../components/BlacklistCard";
import { useNavigate } from "react-router-dom";

const PLATFORMS = [
  { value: "", label: "كل المنصات" },
  { value: "facebook", label: "Facebook" },
  { value: "instagram", label: "Instagram" },
  { value: "tiktok", label: "TikTok" },
];

const SCAM_TYPES = [
  { value: "", label: "كل أنواع النصب" },
  { value: "no_response", label: "لم تصلني البضاعة" },
  { value: "fake_product", label: "المنتج مزيف أو مختلف" },
  { value: "advance_payment", label: "أخذ المال ولم يرد" },
  { value: "ghost_seller", label: "الحساب مزيف" },
  { value: "other", label: "أخرى" },
];

export default function Blacklist() {
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [platform, setPlatform] = useState("");
  const [scamType, setScamType] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const navigate = useNavigate();

  const fetchData = useCallback(() => {
    setLoading(true);
    thiqaApi
      .getBlacklist({ page, search, platform, scam_type: scamType })
      .then((data) => {
        const mapped = (data?.results || []).map((seller) => ({
          id: seller.id,
          username: seller.display_name || seller.profile_url,
          location: seller.category || "غير محدد",
          score: seller.report_count,
          platform: seller.platform,
          aiSummary: `آخر تقرير: ${new Date(seller.latest_report).toLocaleDateString("ar-DZ")} — أنواع الاحتيال: ${seller.scam_types.join(", ")}`,
        }));
        setBlacklist(mapped);
        setTotalPages(data?.pages || 1);
        setTotal(data?.count || 0);
      })
      .catch(() => setBlacklist([]))
      .finally(() => setLoading(false));
  }, [page, search, platform, scamType]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Reset to page 1 when filters change
  useEffect(() => { setPage(1); }, [search, platform, scamType]);

  function handleSearchSubmit(e) {
    e.preventDefault();
    setSearch(searchInput.trim());
  }

  return (
    <main className="blacklist-page" dir="rtl">

      {/* ── Header ── */}
      <div className="bl-header">
        <div className="bl-header-icon"><FiAlertTriangle size={22} /></div>
        <div>
          <h1>القائمة السوداء</h1>
          <p>بائعون تم الإبلاغ عنهم بشكل متكرر من قبل المستعملين</p>
        </div>
      </div>


      {/* ── Filters ── */}
      <div className="bl-filters">
        <form className="bl-search-form" onSubmit={handleSearchSubmit}>
          <div className="bl-search-wrap">
            <FiSearch size={16} className="bl-search-icon" />
            <input
              className="bl-search-input"
              placeholder="ابحث باسم المستخدم أو الرابط..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
            />
            {searchInput && (
              <button
                type="button"
                className="bl-search-clear"
                onClick={() => { setSearchInput(""); setSearch(""); }}
              >×</button>
            )}
          </div>
          <button type="submit" className="bl-search-btn">بحث</button>
        </form>

        <div className="bl-selects">
          <div className="bl-select-wrap">
            <FiFilter size={14} />
            <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="bl-select">
              {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
          <div className="bl-select-wrap">
            <FiFilter size={14} />
            <select value={scamType} onChange={(e) => setScamType(e.target.value)} className="bl-select">
              {SCAM_TYPES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* ── Results count ── */}
      {!loading && (
        <p className="bl-count">
          {total > 0 ? `${total} بائع مبلَّغ عنه` : "لا توجد نتائج"}
        </p>
      )}

      {/* ── List ── */}
      {loading ? (
        <div className="bl-loading">
          <div className="bl-spinner" />
          <span>جاري التحميل...</span>
        </div>
      ) : (
        <div className="bl-list">
          {blacklist.length === 0 ? (
            <div className="bl-empty">
              <FiAlertTriangle size={32} />
              <p>لا توجد نتائج في القائمة السوداء حالياً.</p>
            </div>
          ) : (
            blacklist.map((seller) => (
              <BlacklistCard
                key={seller.id}
                username={seller.username}
                location={seller.location}
                score={seller.score}
                aiSummary={seller.aiSummary}
                onViewProfile={() =>
                  navigate(`/seller/${encodeURIComponent(seller.username)}`)
                }
              />
            ))
          )}
        </div>
      )}

      {/* ── Pagination ── */}
      {totalPages > 1 && (
        <div className="bl-pagination">
          <button
            className="bl-page-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            <FiChevronRight size={18} />
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1)
            .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
            .reduce((acc, p, idx, arr) => {
              if (idx > 0 && p - arr[idx - 1] > 1) acc.push("...");
              acc.push(p);
              return acc;
            }, [])
            .map((p, i) =>
              p === "..." ? (
                <span key={`dots-${i}`} className="bl-dots">…</span>
              ) : (
                <button
                  key={p}
                  className={`bl-page-btn ${page === p ? "active" : ""}`}
                  onClick={() => setPage(p)}
                >
                  {p}
                </button>
              )
            )}

          <button
            className="bl-page-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            <FiChevronLeft size={18} />
          </button>
        </div>
      )}
    </main>
  );
}