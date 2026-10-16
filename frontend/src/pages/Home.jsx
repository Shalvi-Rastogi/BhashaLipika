import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
import SaveToMemory from "../components/SaveToMemory";
import LanguageSelector from "../components/LanguageSelector";
import InputPanel from "../components/Input";
import OutputPanel from "../components/Output";
import TranslateButton from "../components/TranslateButton";
import ResetButton from "../components/ResetButton";
import cdacLogo from "../assets/cdac-logo.png";

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
    <div className="flex min-h-dvh flex-col bg-gray-100 md:h-dvh md:min-h-[620px]">
      <div className="mx-auto flex w-full max-w-none min-h-0 flex-1 flex-col px-4 py-2 sm:px-6 lg:px-8">
        <div className="mb-2 flex items-center justify-between gap-4 px-4 py-2 sm:px-6">
          <div className="min-w-0">
            <h1 className="whitespace-nowrap text-2xl font-semibold leading-tight tracking-tight text-[#193d66] sm:text-3xl">
              Bhasha<span className="text-[#2864e8]">Lipika</span>
            </h1>
            <p className="mt-1 text-sm tracking-[0.2em] text-teal-700 sm:text-base">
              भाषा लिपिका
            </p>
            <span className="mt-1 block h-1 w-10 rounded-full bg-amber-500" />
          </div>
          <img
            src={cdacLogo}
            alt="C-DAC Logo"
            className="w-16 shrink-0 object-contain sm:w-20"
          />
        </div>

        <div className="mb-2">
          <LanguageSelector
            sourceLanguage={sourceLanguage}
            targetLanguage={targetLanguage}
            onSourceLanguageChange={setSourceLanguage}
            onTargetLanguageChange={setTargetLanguage}
          />
        </div>

        {/* INPUT TYPE */}
        <div className="mt-0 flex items-center gap-4">
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
        <div className="mt-1 grid min-h-0 flex-1 grid-cols-1 gap-4 md:grid-cols-2 md:grid-rows-[minmax(350px,1fr)_auto]">
          {/* INPUT */}
          <div className="order-1 flex min-h-0 flex-col md:order-none md:col-start-1 md:row-start-1">
            <InputPanel
              resetKey={resetKey}
              targetLanguage={targetLanguage}
              sourceLanguage={sourceLanguage}
              text={inputText}
              setText={setInputText}
              onDocumentProcessed={handleDocumentProcessed}
            />
          </div>

          {/* OUTPUT */}
          <div className="order-3 min-h-0 md:order-none md:col-start-2 md:row-start-1">
            {documentData ? (
              <OutputPanel
                key={documentData.document_id || "document-output"}
                documentFilename={reconstructedFilename}
                documentId={documentData.document_id}
                onReviewDocument={handleEditDocument}
              />
            ) : (
              <>
                <OutputPanel
                  translatedText={translatedText}
                  targetLanguage={targetLanguage}
                />
              </>
            )}
          </div>

          {/* TEXT BUTTONS */}
          <div className="order-2 mt-1 flex gap-4 md:order-none md:col-start-1 md:row-start-2 md:mt-0">
            <TranslateButton onTranslate={handleTranslate} />
            <ResetButton onReset={handleReset} />
          </div>
        </div>

      </div>
    </div>
  );
}

export default Home;