function ResetButton({ onReset }) {
  return (
    <button
      onClick={onReset}
      className="
        bg-gray-200
        hover:bg-gray-300
        text-gray-800
        font-semibold
        px-10
        py-3
        rounded-lg
        shadow-md
        transition
        duration-300
      "
    >
      Reset
    </button>
  );
}

export default ResetButton;