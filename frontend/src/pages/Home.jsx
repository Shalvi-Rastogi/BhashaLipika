import { useState } from "react";
import axios from "axios";
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

  // Selected target language
  const [targetLanguage, setTargetLanguage] = useState("");

  const handleTranslate = async () => {
    if (!inputText.trim()) {
      alert("Please enter some text to translate.");
      return;
    }

    if (!targetLanguage) {
      alert("Please select a target language.");
      return;
    }

    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/translate",
        {
          text: inputText,
          target_language: targetLanguage,
        }
      );

      console.log("Translation response:", response.data);

      setTranslatedText(response.data.translated_text);
    } catch (error) {
      console.error("Translation failed:", error);

      alert(
        error.response?.data?.detail ||
        "Translation failed. Please try again."
      );
    }
  };

  const handleReset = () => {
    setInputText("");
    setTranslatedText("");
    setResetKey((prev) => prev + 1);

    // Clear selected target language
    setTargetLanguage("");
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">

        {/* Language Selection */}
        <LanguageSelector
          onLanguageChange={setTargetLanguage}
          resetKey={resetKey}
        />

        {/* Input & Output */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

          {/* LEFT SIDE */}
          <div>
            <InputPanel
              resetKey={resetKey}
              targetLanguage={targetLanguage}
              text={inputText}
              setText={setInputText}
            />

            {/* Translate & Reset Buttons */}
            <div className="mt-5 flex gap-4">
              <TranslateButton onTranslate={handleTranslate} />

              <ResetButton
                onReset={handleReset}
              />
            </div>
          </div>

          {/* RIGHT SIDE */}
          <div>
            <OutputPanel translatedText={translatedText} />

            {/* Download & Save Buttons */}
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