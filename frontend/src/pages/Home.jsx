// import { useState } from "react";
// import { useNavigate } from "react-router-dom";
// import axios from "axios";
// import LanguageSelector from "../components/LanguageSelector";
// import InputPanel from "../components/Input";
// import OutputPanel from "../components/Output";
// import TranslateButton from "../components/TranslateButton";
// import ResetButton from "../components/ResetButton";
// import SaveToMemory from "../components/SaveToMemory";
// import DownloadDocument from "../components/DownloadDocument";

// function Home() {
//   const navigate = useNavigate();
//   const [inputText, setInputText] = useState("");
//   const [translatedText, setTranslatedText] = useState("");
//   const [documentData, setDocumentData] = useState(null);
//   const [resetKey, setResetKey] = useState(0);

//   // Selected target language
//   const [targetLanguage, setTargetLanguage] = useState("");
//   const handleDocumentProcessed = (data) => {
//     console.log("Processed document data:", data);

//     setDocumentData(data);

//     navigate("/review", {
//       state: {
//         documentData: data,
//       },
//     });
//   };

//   const handleTranslate = async () => {
//     if (!inputText.trim()) {
//       alert("Please enter some text to translate.");
//       return;
//     }

//     if (!targetLanguage) {
//       alert("Please select a target language.");
//       return;
//     }

//     try {
//       const response = await axios.post(
//         "http://127.0.0.1:8000/translate",
//         {
//           text: inputText,
//           target_language: targetLanguage,
//         }
//       );

//       console.log("Translation response:", response.data);

//       setTranslatedText(response.data.translated_text);
//     } catch (error) {
//       console.error("Translation failed:", error);

//       alert(
//         error.response?.data?.detail ||
//         "Translation failed. Please try again."
//       );
//     }
//   };

//   const handleReset = () => {
//     setInputText("");
//     setTranslatedText("");
//     setResetKey((prev) => prev + 1);

//     // Clear selected target language
//     setTargetLanguage("");
//   };

//   return (
//     <div className="min-h-screen bg-gray-100 p-8">
//       <div className="max-w-6xl mx-auto">

//         {/* Language Selection */}
//         <LanguageSelector
//           onLanguageChange={setTargetLanguage}
//           resetKey={resetKey}
//         />

//         {/* Input & Output */}
//         <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

//           {/* LEFT SIDE */}
//           <div>
//             <InputPanel
//               resetKey={resetKey}
//               targetLanguage={targetLanguage}
//               text={inputText}
//               setText={setInputText}
//               onDocumentProcessed={handleDocumentProcessed}
//             />

//             {/* Translate & Reset Buttons */}
//             <div className="mt-5 flex gap-4">
//               <TranslateButton onTranslate={handleTranslate} />

//               <ResetButton
//                 onReset={handleReset}
//               />
//             </div>
//           </div>

//           {/* RIGHT SIDE */}
//           <div>
//             <OutputPanel translatedText={translatedText} />

//             {/* Download & Save Buttons */}
//             <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
//               <DownloadDocument />
//               <SaveToMemory />
//             </div>
//           </div>

//         </div>
//       </div>
//     </div>
//   );
// }

// export default Home;
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

import LanguageSelector from "../components/LanguageSelector";
import InputPanel from "../components/Input";
import OutputPanel from "../components/Output";
import TranslateButton from "../components/TranslateButton";
import ResetButton from "../components/ResetButton";
import SaveToMemory from "../components/SaveToMemory";
import DownloadDocument from "../components/DownloadDocument";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Home() {
  const navigate = useNavigate();
  const location = useLocation();

  const [inputText, setInputText] = useState(
    location.state?.inputText || ""
  );
  const [documentData, setDocumentData] = useState(
    location.state?.documentData || null
  );
  const [translatedText, setTranslatedText] = useState("");
  const [targetLanguage, setTargetLanguage] = useState(
    location.state?.targetLanguage || ""
  );
  const [sourceLanguage, setSourceLanguage] = useState(
    location.state?.sourceLanguage || "en"
  );
  const [resetKey, setResetKey] = useState(0);

  // Processed document
  //const [documentData, setDocumentData] = useState(null);

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

  const savedState = sessionStorage.getItem(
    "translatorHomeState"
  );

  if (savedState) {
    try {
      const state = JSON.parse(savedState);

      setInputText(state.inputText || "");
      setTranslatedText(state.translatedText || "");
      setTargetLanguage(state.targetLanguage || "");
      setSourceLanguage(state.sourceLanguage || "en");
      setDocumentData(state.documentData || null);

    } catch (error) {
      console.error(
        "Failed to restore Home state:",
        error
      );
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
  }, [
    inputText,
    translatedText,
    sourceLanguage,
    targetLanguage,
    documentData,
  ]);

  // ------------------------------------------------
  // TEXT TRANSLATION
  // ------------------------------------------------
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
        `${API_BASE_URL}/translate`,
        {
          text: inputText,
          source_language: sourceLanguage,
          target_language: targetLanguage,
        }
      );

      console.log(
        "Translation response:",
        response.data
      );

      setTranslatedText(
        response.data.translated_text
      );

    } catch (error) {
      console.error(
        "Translation failed:",
        error
      );

      alert(
        error.response?.data?.detail ||
          "Translation failed. Please try again."
      );
    }
  };

  // ------------------------------------------------
  // DOCUMENT PROCESSED
  // ------------------------------------------------
  const handleDocumentProcessed = (data) => {
    console.log(
      "Processed document data:",
      data
    );

    setDocumentData(data);

    // Clear normal text translation
    setInputText("");
    setTranslatedText("");
  };

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
    // setInputText("");
    // setTranslatedText("");
    // setTargetLanguage("");
    // setDocumentData(null);

    // setResetKey(
    //   (previous) => previous + 1
    // );

    // sessionStorage.removeItem(
    //   "translatorHomeState"
    // );
    setInputText("");
    setTranslatedText("");
    setDocumentData(null);
    setSourceLanguage("en");
    setTargetLanguage("");

    setResetKey((prev) => prev + 1);

    sessionStorage.removeItem("translatorHomeState");
  };

  const isExcelDocument = [
    documentData?.file_type,
    documentData?.data?.document_type,
    documentData?.filename,
    documentData?.data?.filename,
  ].some((value) => /(?:xls[x]?|excel)/i.test(value || ""));
  const isWordDocument = [
    documentData?.file_type,
    documentData?.data?.document_type,
    documentData?.filename,
    documentData?.data?.filename,
  ].some((value) => /(?:docx?|word)/i.test(value || ""));

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

        {/* INPUT / OUTPUT */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">

          {/* LEFT */}
          <div>

            <InputPanel
              resetKey={resetKey}
              targetLanguage={
                targetLanguage
              }
              sourceLanguage={sourceLanguage}
              text={inputText}
              setText={setInputText}
              onDocumentProcessed={
                handleDocumentProcessed
              }
            />

            {/* TEXT BUTTONS */}
            <div className="mt-5 flex gap-4">

              <TranslateButton
                onTranslate={
                  handleTranslate
                }
              />

              <ResetButton
                onReset={handleReset}
              />

            </div> 
                  
          </div>

          {/* RIGHT */}
          <div>

            {/* NORMAL TEXT TRANSLATION */}
            { (
              <>
                <OutputPanel
                  translatedText={
                    translatedText
                  }

                />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">

                  <DownloadDocument />

                  <SaveToMemory />

                </div>
              </>
            )}

          </div>

        </div>

        {/* ================================================= */}
        {/* TRANSLATED DOCUMENT PREVIEW */}
        {/* ================================================= */}

        {documentData && (
          <div className="mt-10">

            <div className="bg-white rounded-2xl shadow-md p-6">

              {/* HEADER */}
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">

                <div>

                  <h2 className="text-2xl font-bold text-gray-800">
                    {isExcelDocument || isWordDocument ? "Review Reconstructed Document" : "Translated Document"}
                  </h2>

                  <p className="text-gray-500 mt-1">
                    {documentData.data?.filename ||
                      documentData.filename ||
                      "Translated Document"}
                  </p>

                </div>

                <div className="flex gap-3">

                  {/* EDIT */}
                  <button
                    type="button"
                    onClick={
                      handleEditDocument
                    }
                    className="
                      bg-violet-600
                      hover:bg-violet-700
                      text-white
                      font-semibold
                      px-5
                      py-3
                      rounded-lg
                      transition
                    "
                  >
                    {isExcelDocument
                      ? "Review Excel Workbook"
                      : isWordDocument
                        ? "Review Word Document"
                        : "Edit Reconstructed Document"}
                  </button>

                </div>

              </div>

              {/* SHEETS */}
              {!isExcelDocument && !isWordDocument && documentData.data?.sheets?.map(
                (sheet, sheetIndex) => (

                  <div
                    key={sheetIndex}
                    className="mb-8 last:mb-0"
                  >

                    <h3 className="text-xl font-semibold mb-4">
                      {sheet.sheet_name}
                    </h3>

                    <div className="overflow-x-auto border rounded-xl">

                      <table className="w-full border-collapse">

                        <thead>

                          <tr className="bg-gray-100">

                            <th className="border p-3 text-left">
                              Cell
                            </th>

                            <th className="border p-3 text-left">
                              Original Text
                            </th>

                            <th className="border p-3 text-left">
                              Translated Text
                            </th>

                          </tr>

                        </thead>

                        <tbody>

                          {sheet.cells?.map(
                            (cell, cellIndex) => (

                              <tr
                                key={cellIndex}
                              >

                                <td className="border p-3 font-semibold text-gray-700">
                                  {
                                    cell.coordinate
                                  }
                                </td>

                                <td className="border p-3 text-gray-700">
                                  {
                                    cell.original_text ||
                                    ""
                                  }
                                </td>

                                <td className="border p-3 text-gray-800">
                                  {
                                    cell.translated_text ||
                                    ""
                                  }
                                </td>

                              </tr>

                            )
                          )}

                        </tbody>

                      </table>

                    </div>

                  </div>

                )
              )}

            </div>

          </div>
        )}

      </div>

    </div>
  );
}

export default Home;