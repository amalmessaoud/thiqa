import "./AiVerdict.css";
import starIcon from "../assets/star.svg";

export default function AiVerdict({ text }) {
  return (
    <div className="ai-verdict">
      <img src={starIcon} alt="" className="ai-verdict-icon" />
      <p>{text}</p>
    </div>
  );
}