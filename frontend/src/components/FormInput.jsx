import "./FormInput.css";

export default function FormInput({ label, type = "text", placeholder, value, onChange, icon, onIconClick }) {
  return (
    <div className="form-input-group">
      {label && <label className="form-input-label">{label}</label>}
      <div className="form-input-wrapper">
        <input
          className="form-input"
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={onChange}
        />
        {icon && (
          <button className="form-input-icon" onClick={onIconClick} type="button">
            {icon}
          </button>
        )}
      </div>
    </div>
  );
}