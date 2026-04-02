import "./ReviewCard.css";

function Stars({ count }) {
  return (
    <div className="review-card-stars">
      {[1, 2, 3, 4, 5].map((s) => (
        <span key={s} style={{ color: s <= count ? "#f5a623" : "#ddd" }}>★</span>
      ))}
    </div>
  );
}

export default function ReviewCard({ name, initials, date, rating, tags, comment }) {
  return (
    <div className="review-card-item">
      <div className="review-card-top">
        <div className="review-card-meta">
          {initials && <div className="review-card-avatar">{initials}</div>}
          <div>
            <p className="review-card-name">{name}</p>
            <p className="review-card-date">{date}</p>
          </div>
        </div>
        <Stars count={rating} />
      </div>
      {tags && tags.length > 0 && (
        <div className="review-card-tags">
          {tags.map((t) => (
            <span key={t} className="review-card-tag">✓ {t}</span>
          ))}
        </div>
      )}
      {comment && <p className="review-card-comment">{comment}</p>}
    </div>
  );
}