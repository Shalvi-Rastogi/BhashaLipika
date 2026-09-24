function TranslateButton({ onTranslate}) {
  return (
    <button
      type="button"
      onClick={onTranslate}
      className="
        bg-violet-600
        hover:bg-violet-700
        text-white
        font-semibold
        px-10
        py-3
        rounded-lg
        shadow-md
        transition
        duration-300
      "
    >
      Translate
    </button>
  );
}

export default TranslateButton;