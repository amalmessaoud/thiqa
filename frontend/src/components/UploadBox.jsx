import "./UploadBox.css";
import { FiImage } from "react-icons/fi";

export default function UploadBox({ images, onChange, hint }) {
  return (
    <label className="upload-box">
      <input type="file" accept="image/*" multiple onChange={onChange} hidden />
      {images && images.length > 0 ? (
        <div className="upload-box-filelist">
          {Array.from(images).map((img, i) => (
            <span key={i} className="upload-box-filename">✅ {img.name}</span>
          ))}
        </div>
      ) : (
        <div className="upload-box-placeholder">
          <FiImage size={36} />
          <span>اضغط لرفع صور</span>
          {hint && <small>{hint}</small>}
        </div>
      )}
    </label>
  );
}