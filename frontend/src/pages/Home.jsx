import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

import LanguageSelector from "../components/LanguageSelector";
import InputPanel from "../components/Input";
import OutputPanel from "../components/Output";
import TranslateButton from "../components/TranslateButton";
import ResetButton from "../components/ResetButton";
import DownloadDocument from "../components/DownloadDocument";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Home() {
  const navigate = useNavigate();
  const location = useLocation();

  const [inputText, setInputText] = useState(location.state?.inputText || "");
  const [documentData, setDocumentData] = useState(location.state?.documentData || null);
  const [translatedText, setTranslatedText] = useState("");
  const [targetLanguage, setTargetLanguage] = useState(location.state?.targetLanguage || "");
  const [sourceLanguage, setSourceLanguage] = useState(location.state?.sourceLanguage || "en");
  const [resetKey, setResetKey] = useState(0);
  const [inputType, setInputType] = useState("text");

  // ------------------------------------------------
  // RESTORE HOME STATE
  // ------------------------------------------------
  useEffect(() => {
    if (location.state) {
      setInputText(location.state.inputText || "");
      setTranslatedText(location.state.translatedText || "");
      setTargetLanguage(location.state.targetLanguage || "");
      setSourceLanguage(location.state.sourceLanguage || "en");

      if (location.state.documentData) {
        setDocumentData(location.state.documentData);
      }
      return;
    }

    const savedState = sessionStorage.getItem("translatorHomeState");

    if (savedState) {
      try {
        const state = JSON.parse(savedState);
        setInputText(state.inputText || "");
        setTranslatedText(state.translatedText || "");
        setTargetLanguage(state.targetLanguage || "");
        setSourceLanguage(state.sourceLanguage || "en");
        setDocumentData(state.documentData || null);
      } catch (error) {
        console.error("Failed to restore Home state:", error);
      }
    }
  }, [location.state]);

  // ------------------------------------------------
  // SAVE HOME STATE
  // ------------------------------------------------
  useEffect(() => {
    sessionStorage.setItem(
      "translatorHomeState",
      JSON.stringify({
        inputText,
        translatedText,
        sourceLanguage,
        targetLanguage,
        documentData,
      })
    );
  }, [inputText, translatedText, sourceLanguage, targetLanguage, documentData]);

  // ------------------------------------------------
  // TEXT TRANSLATION
  // ------------------------------------------------
  const handleTranslate = async () => {
    if (!inputText.trim()) {
      alert("Please enter some content to translate.");
      return;
    }
    if (!sourceLanguage) {
      alert("Please select a source language.");
      return;
    }
    if (!targetLanguage) {
      alert("Please select a target language.");
      return;
    }
    if (sourceLanguage === targetLanguage) {
      alert("Source and target languages must be different.");
      return;
    }

    try {
      let response;

      // HTML TRANSLATION
      if (inputType === "html") {
        response = await axios.post(
          `${API_BASE_URL}/translate-html`,
          {
            html: inputText,
            source_language: sourceLanguage, 
            target_language: targetLanguage,
          }
        );

        console.log("HTML Translation response:", response.data);
        setTranslatedText(response.data.translated_html);

      }
      // NORMAL TEXT TRANSLATION
      else {
        response = await axios.post(
          `${API_BASE_URL}/translate`,
          {
            text: inputText,
            source_language: sourceLanguage, // Samia's change
            target_language: targetLanguage,
          }
        );

        console.log("Translation response:", response.data);
        setTranslatedText(response.data.translated_text);
      }
    } catch (error) {
      console.error("Translation failed:", error);
      alert(error.response?.data?.detail || "Translation failed. Please try again.");
    }
  };

  // ------------------------------------------------
  // DOCUMENT PROCESSED
  // ------------------------------------------------
  const handleDocumentProcessed = (data) => {
    console.log("Processed document data:", data);
    setDocumentData(data);
    setInputText("");
    setTranslatedText("");
  };

  const reconstructedFilename =
    documentData?.reconstructed_rtf_file ||
    documentData?.reconstructed_docx_file ||
    documentData?.reconstructed_xlsx_file ||
    documentData?.reconstructed_pptx_file ||
    documentData?.reconstructed_pdf_file ||
    documentData?.reconstructed_file ||
    documentData?.output_filename ||
    "";

  // ------------------------------------------------
  // OPEN REVIEW PAGE
  // ------------------------------------------------
  const handleEditDocument = () => {
    navigate("/review", {
      state: {
        documentData: documentData,
        targetLanguage: targetLanguage,
        sourceLanguage: sourceLanguage,
        inputText: inputText,
        translatedText: translatedText,
      },
    });
  };

  // ------------------------------------------------
  // RESET EVERYTHING
  // ------------------------------------------------
  const handleReset = () => {
    setInputText("");
    setTranslatedText("");
    setDocumentData(null);
    setSourceLanguage("en");
    setTargetLanguage("");
    setInputType("text");
    setResetKey((prev) => prev + 1);
    sessionStorage.removeItem("translatorHomeState");
  };

  // ------------------------------------------------
  // RETURN
  // ------------------------------------------------
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* LANGUAGE */}
        <LanguageSelector
          sourceLanguage={sourceLanguage}
          targetLanguage={targetLanguage}
          onSourceLanguageChange={setSourceLanguage}
          onTargetLanguageChange={setTargetLanguage}
        />

        {/* INPUT TYPE */}
        <div className="mt-6 flex items-center gap-6">
          <span className="font-semibold text-gray-700">Input Type:</span>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="inputType"
              value="text"
              checked={inputType === "text"}
              onChange={() => setInputType("text")}
            />
            <span>Text</span>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="inputType"
              value="html"
              checked={inputType === "html"}
              onChange={() => setInputType("html")}
            />
            <span>HTML</span>
          </label>
        </div>

        {/* INPUT / OUTPUT */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          {/* LEFT */}
          <div>
            <InputPanel
              resetKey={resetKey}
              targetLanguage={targetLanguage}
              sourceLanguage={sourceLanguage}
              text={inputText}
              setText={setInputText}
              onDocumentProcessed={handleDocumentProcessed}
            />
            {/* TEXT BUTTONS */}
            <div className="mt-5 flex gap-4">
              <TranslateButton onTranslate={handleTranslate} />
              <ResetButton onReset={handleReset} />
            </div>
          </div>

          {/* RIGHT */}
          <div>
            {/* NORMAL TEXT TRANSLATION */}
            {(
              <>
                <OutputPanel
                  key={documentData?.document_id || "text-translation"}
                  translatedText={translatedText}
                  documentFilename={reconstructedFilename}
                  documentId={documentData?.document_id}
                  onReviewDocument={handleEditDocument}
                />
                {!documentData && (
                  <div className="mt-5">
                    <DownloadDocument />
                  </div>
                )}
              </>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

export default Home;