import "./ResultsPlaceholder.css";
import starIcon from "../assets/star.svg";

export default function ResultsPlaceholder({ message = 'ارفع صورة واضغط "تحليل" لرؤية النتائج' }) {
  return (
    <div className="results-placeholder">
      <img src={starIcon} alt="star" className="results-placeholder-icon" />
      <p>{message}</p>
    </div>
  );
}