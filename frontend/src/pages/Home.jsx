import { useState } from "react";
import LanguageSelector from "../components/LanguageSelector";
import InputPanel from "../components/Input";
import OutputPanel from "../components/Output";
import TranslateButton from "../components/TranslateButton";
import ResetButton from "../components/ResetButton";
import SaveToMemory from "../components/SaveToMemory";
import DownloadDocument from "../components/DownloadDocument";

function Home() {
  const [inputText, setInputText] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [resetKey, setResetKey] = useState(0);
  const handleReset = () => {
  setInputText("");
  setTranslatedText("");
  setResetKey((prev) => prev + 1);
 };
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">

        {/* Language Selection */}
        <LanguageSelector />

        {/* Input & Output */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

          {/* LEFT SIDE */}
          <div>
            <InputPanel resetKey={resetKey} />

            {/* Translate Button */}
            <div className="mt-5 flex gap-4">
               <TranslateButton />
               <ResetButton onReset={handleReset} />
            </div>
          </div>

          {/* RIGHT SIDE */}
          <div>
             <OutputPanel />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
             <DownloadDocument />
           <SaveToMemory />
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

export default Home;