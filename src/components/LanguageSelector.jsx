import { ArrowRightLeft } from "lucide-react";

function LanguageSelector() {
  const languages = [
    { code: "en", name: "English" },
    { code: "hi", name: "Hindi" },
    { code: "mr", name: "Marathi" },
    { code: "ur", name: "Urdu" },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 flex flex-col md:flex-row items-center justify-between gap-4">
      
      {/* Source Language */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-600 mb-2">
          Source Language
        </label>

        <select className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500">
          {languages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      {/* Swap Button */}
      <button className="bg-purple-600 hover:bg-purple-700 text-white p-3 rounded-full transition duration-300 mt-6 md:mt-0">
        <ArrowRightLeft size={20} />
      </button>

      {/* Target Language */}
      <div className="w-full">
        <label className="block text-sm font-medium text-gray-600 mb-2">
          Target Language
        </label>

        <select className="w-full border border-gray-300 rounded-xl px-4 py-3 outline-none focus:ring-2 focus:ring-purple-500">
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