import "./PrimaryButton.css";

export default function PrimaryButton({
  children,
  onClick,
  type = "button",
  fullWidth = false,
  variant = "dark",
}) {
  return (
    <button
      className={`primary-btn variant-${variant} ${fullWidth ? "full-width" : ""}`}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  );
}