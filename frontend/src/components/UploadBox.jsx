import "./UploadBox.css";
import { FiImage } from "react-icons/fi";

export default function UploadBox({ image, onChange, hint }) {
  return (
    <label className="upload-box">
      <input type="file" accept="image/*" onChange={onChange} hidden />
      {image ? (
        <span className="upload-box-filename">✅ {image.name}</span>
      ) : (
        <div className="upload-box-placeholder">
          <FiImage size={36} />
          <span>اضغط لرفع صورة</span>
          {hint && <small>{hint}</small>}
        </div>
      )}
    </label>
  );
}