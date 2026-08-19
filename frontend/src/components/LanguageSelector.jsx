import { useState } from "react";
import { ArrowRightLeft } from "lucide-react";

function LanguageSelector({ onLanguageChange }) {
  const languages = [
    { code: "en", name: "English" },
    { code: "hi", name: "Hindi" },
    { code: "mr", name: "Marathi" },
    { code: "ur", name: "Urdu" },
  ];

  // Source language is currently English
  const [sourceLanguage, setSourceLanguage] = useState("en");

  // No target language selected initially
  const [targetLanguage, setTargetLanguage] = useState("");

  const handleTargetChange = (e) => {
    const value = e.target.value;

    setTargetLanguage(value);

    if (onLanguageChange) {
      onLanguageChange(value);
    }
  };

  const handleSwap = () => {
    const oldSource = sourceLanguage;
    const oldTarget = targetLanguage;

    // Don't swap if target language is not selected
    if (!oldTarget) {
      return;
    }

    setSourceLanguage(oldTarget);
    setTargetLanguage(oldSource);

    if (onLanguageChange) {
      onLanguageChange(oldSource);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 flex flex-col md:flex-row items-center justify-between gap-4">

      {/* Source Language */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-600 mb-2">
          Source Language
        </label>

        <select
          value={sourceLanguage}
          onChange={(e) => setSourceLanguage(e.target.value)}
          className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500"
        >
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Swap Button */}
      <button
        type="button"
        onClick={handleSwap}
        className="bg-purple-600 hover:bg-purple-700 text-white p-3 rounded-full transition duration-300 mt-6 md:mt-0"
      >
        <ArrowRightLeft size={20} />
      </button>

      {/* Target Language */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-600 mb-2">
          Target Language
        </label>

        <select
          value={targetLanguage}
          onChange={handleTargetChange}
          className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="" disabled>
            Select Target Language
          </option>

          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

export default LanguageSelector;