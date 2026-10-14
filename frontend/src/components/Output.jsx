// import { useState, useEffect } from "react";
// import {
//   Copy,
//   Check,
//   Volume2,
//   VolumeX,
// } from "lucide-react";

// function OutputPanel({
//   translatedText,
//   targetLanguage = "hi",
// }) {
//   const [copied, setCopied] = useState(false);
//   const [speaking, setSpeaking] = useState(false);

//   useEffect(() => {
//     return () => {
//       window.speechSynthesis?.cancel();
//     };
//   }, []);

//   const handleCopy = async () => {
//     if (!translatedText?.trim()) return;

//     try {
//       await navigator.clipboard.writeText(translatedText);
//       setCopied(true);

//       setTimeout(() => setCopied(false), 2000);
//     } catch (error) {
//       console.error("Failed to copy translation:", error);
//     }
//   };

//   const handleSpeak = () => {
//     if (!translatedText?.trim()) return;

//     const speech = window.speechSynthesis;

//     if (!speech) {
//       alert("Text-to-speech is not supported by this browser.");
//       return;
//     }

//     if (speaking) {
//       speech.cancel();
//       setSpeaking(false);
//       return;
//     }

//     speech.cancel();

//     const utterance = new SpeechSynthesisUtterance(
//       translatedText
//     );

//     const languageMap = {
//       en: "en-US",
//       hi: "hi-IN",
//       mr: "mr-IN",
//       ur: "ur-PK",
//     };

//     utterance.lang =
//       languageMap[targetLanguage] || targetLanguage || "hi-IN";

//     utterance.onstart = () => setSpeaking(true);

//     utterance.onend = () => setSpeaking(false);

//     utterance.onerror = () => setSpeaking(false);

//     speech.speak(utterance);
//   };

//   return (
//     <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">
//       <div className="flex items-center justify-between mb-4">
//         <h2 className="text-xl font-semibold">
//           Translated Text
//         </h2>

//         <div className="flex items-center gap-2">
//           <button
//             type="button"
//             onClick={handleSpeak}
//             disabled={!translatedText?.trim()}
//             title={speaking ? "Stop speaking" : "Listen to translation"}
//             aria-label={speaking ? "Stop speaking" : "Listen to translation"}
//             className="flex items-center gap-2 rounded-lg p-2
//                        text-gray-600 hover:bg-gray-100
//                        disabled:opacity-40 transition-colors"
//           >
//             {speaking ? (
//               <VolumeX size={20} className="text-blue-600" />
//             ) : (
//               <Volume2 size={20} />
//             )}
//           </button>

//           <button
//             type="button"
//             onClick={handleCopy}
//             disabled={!translatedText?.trim()}
//             title={copied ? "Copied!" : "Copy translation"}
//             aria-label="Copy translated text"
//             className="flex items-center gap-2 rounded-lg p-2
//                        text-gray-600 hover:bg-gray-100
//                        disabled:opacity-40 transition-colors"
//           >
//             {copied ? (
//               <>
//                 <Check size={18} className="text-green-600" />
//                 <span className="text-sm text-green-600">
//                   Copied!
//                 </span>
//               </>
//             ) : (
//               <>
//                 <Copy size={18} />
//                 <span className="text-sm">Copy</span>
//               </>
//             )}
//           </button>
//         </div>
//       </div>

//       <textarea
//         value={translatedText || ""}
//         readOnly
//         placeholder="Translation will appear here..."
//         className="w-full h-[340px] border rounded-xl p-4 resize-none
//                    bg-gray-50"
//       />
//     </div>
//   );
// }
// import { Download, Eye, FileText, Pencil, X } from "lucide-react";
// //import { useEffect, useState } from "react";

// const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// function OutputPanel({
//   translatedText,
//   documentFilename,
//   documentId,
//   onReviewDocument,
// }) {
//   const [isPreviewing, setIsPreviewing] = useState(false);
//   const fileExtension = documentFilename?.split(".").pop()?.toUpperCase();

//   useEffect(() => {
//     if (!isPreviewing) return undefined;

//     const handleKeyDown = (event) => {
//       if (event.key === "Escape") {
//         setIsPreviewing(false);
//       }
//     };

//     window.addEventListener("keydown", handleKeyDown);
//     return () => window.removeEventListener("keydown", handleKeyDown);
//   }, [isPreviewing]);

//   return (
//     <>
//       <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">
//         <h2 className="text-xl font-semibold mb-4">
//           {documentFilename ? "Translated Document" : "Translated Text"}
//         </h2>

//         {documentFilename ? (
//           <div className="h-[340px] border rounded-xl bg-gray-50 p-4 flex flex-col items-center justify-center text-center">
//             <FileText size={48} className="text-violet-600 mb-4" />
//             <p className="text-sm text-gray-500 mb-3">
//               Your reconstructed translation is ready.
//             </p>
//             <button
//               type="button"
//               onClick={() => setIsPreviewing(true)}
//               disabled={!documentId}
//               className="max-w-full inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-3 font-semibold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-gray-400"
//               title={`Preview ${documentFilename}`}
//             >
//               <span className="min-w-0 truncate">{documentFilename}</span>
//               <Eye size={18} className="shrink-0" />
//             </button>
//             <button
//               type="button"
//               onClick={onReviewDocument}
//               disabled={!documentId}
//               className="mt-4 inline-flex items-center gap-2 rounded-lg border border-violet-600 px-4 py-2 font-semibold text-violet-700 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:border-gray-300 disabled:text-gray-400"
//             >
//               <Pencil size={16} />
//               Review &amp; Edit (HITL)
//             </button>
//             <p className="text-xs text-gray-500 mt-3">
//               Preview the reconstructed file or open it for human review and editing.
//             </p>
//           </div>
//         ) : (
//           <textarea
//             value={translatedText}
//             readOnly
//             placeholder="Translation will appear here..."
//             className="w-full h-[340px] border rounded-xl p-4 resize-none
//                        bg-gray-50"
//           />
//         )}
//       </div>

//       {isPreviewing && documentId && (
//         <div
//           className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-3 sm:p-6"
//           role="presentation"
//           onMouseDown={(event) => {
//             if (event.target === event.currentTarget) {
//               setIsPreviewing(false);
//             }
//           }}
//         >
//           <section
//             role="dialog"
//             aria-modal="true"
//             aria-label={`Preview of ${documentFilename}`}
//             className="flex h-[94vh] w-full max-w-[1600px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
//           >
//             <header className="flex min-h-14 items-center justify-between gap-4 border-b px-4 py-3 sm:px-6">
//               <h2 className="min-w-0 truncate text-base font-semibold text-gray-800 sm:text-lg">
//                 {documentFilename}
//               </h2>
//               <div className="flex shrink-0 items-center gap-2">
//                 <a
//                   href={`${API_BASE_URL}/review/download/${documentId}`}
//                   className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-violet-700"
//                   title={`Download reconstructed ${fileExtension} file`}
//                 >
//                   <Download size={18} />
//                   <span>Download {fileExtension}</span>
//                 </a>
//                 <button
//                   type="button"
//                   onClick={() => setIsPreviewing(false)}
//                   className="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100"
//                   aria-label="Close preview"
//                 >
//                   <span className="hidden sm:inline">Close preview</span>
//                   <X size={20} />
//                 </button>
//               </div>
//             </header>
//             <iframe
//               key={documentId}
//               title={`Preview of ${documentFilename}`}
//               src={`${API_BASE_URL}/review/preview/${documentId}#toolbar=0&navpanes=0`}
//               className="min-h-0 w-full flex-1 bg-gray-100"
//             />
//           </section>
//         </div>
//       )}
//     </>
//   );
// }

// export default OutputPanel;

import { useEffect, useState } from "react";
import {
  Copy,
  Check,
  Volume2,
  VolumeX,
  Download,
  Eye,
  FileText,
  Pencil,
  X,
} from "lucide-react";
import DownloadDocument from "./DownloadDocument";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function OutputPanel({
  translatedText = "",
  targetLanguage = "hi",
  documentFilename,
  documentId,
  onReviewDocument,
}) {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  useEffect(() => {
    if (!isPreviewing) return;

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsPreviewing(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isPreviewing]);

  const handleCopy = async () => {
    if (!translatedText.trim()) return;

    try {
      await navigator.clipboard.writeText(translatedText);
      setCopied(true);

      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy translation:", error);
    }
  };

  const handleSpeak = () => {
    if (!translatedText.trim()) return;

    const speech = window.speechSynthesis;

    if (!speech) {
      alert("Text-to-speech is not supported by this browser.");
      return;
    }

    if (speaking) {
      speech.cancel();
      setSpeaking(false);
      return;
    }

    speech.cancel();

    const utterance = new SpeechSynthesisUtterance(translatedText);

    const languageMap = {
      en: "en-US",
      hi: "hi-IN",
      mr: "mr-IN",
      ur: "ur-PK",
    };

    utterance.lang =
      languageMap[targetLanguage] || targetLanguage || "hi-IN";

    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);

    speech.speak(utterance);
  };

  return (
    <>
      <div className="bg-white rounded-2xl shadow-md p-5 h-full min-h-[350px] flex flex-col">
        <div className="flex items-center justify-between mb-4 gap-2">
          <h2 className="text-xl font-semibold">
            {documentFilename ? "Translated Document" : "Translated Text"}
          </h2>

          {!documentFilename && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={handleSpeak}
                disabled={!translatedText.trim()}
                title={speaking ? "Stop speaking" : "Listen to translation"}
                aria-label={speaking ? "Stop speaking" : "Listen to translation"}
                className="rounded-lg p-2 text-gray-600 hover:bg-gray-100
                           disabled:opacity-40 transition-colors"
              >
                {speaking ? (
                  <VolumeX size={20} className="text-blue-600" />
                ) : (
                  <Volume2 size={20} />
                )}
              </button>

              <button
                type="button"
                onClick={handleCopy}
                disabled={!translatedText.trim()}
                title={copied ? "Copied!" : "Copy translation"}
                aria-label="Copy translated text"
                className="flex items-center gap-2 rounded-lg p-2
                           text-gray-600 hover:bg-gray-100
                           disabled:opacity-40 transition-colors"
              >
                {copied ? (
                  <>
                    <Check size={18} className="text-green-600" />
                    <span className="text-sm text-green-600">
                      Copied!
                    </span>
                  </>
                ) : (
                  <>
                    <Copy size={18} />
                    <span className="text-sm">Copy</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>

        {documentFilename ? (
          <div className="flex min-h-0 flex-1 flex-col items-center justify-center
                          rounded-xl border border-gray-200 bg-gray-50 px-5 py-6
                          text-center">
            <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-violet-100 text-violet-700">
              <FileText size={25} aria-hidden="true" />
            </div>
            <p className="mb-4 text-sm text-gray-600">
              Your reconstructed translation is ready
            </p>
            <button
              type="button"
              onClick={() => setIsPreviewing(true)}
              disabled={!documentId}
              className="inline-flex max-w-full items-center justify-center gap-2
                         rounded-lg bg-violet-600 px-4 py-3 font-semibold text-white
                         shadow-sm transition hover:bg-violet-700
                         focus:outline-none focus:ring-2 focus:ring-violet-300
                         focus:ring-offset-2 disabled:bg-gray-400 sm:min-w-0"
              title={`Preview ${documentFilename}`}
            >
              <span className="min-w-0 truncate">{documentFilename}</span>
              <Eye size={18} className="shrink-0" aria-hidden="true" />
            </button>
            <button
              type="button"
              onClick={onReviewDocument}
              disabled={!documentId || !onReviewDocument}
              className="mt-3 inline-flex items-center justify-center gap-2
                         rounded-lg border border-violet-200 bg-white px-4 py-2.5
                         font-semibold text-violet-700 transition hover:bg-violet-50
                         focus:outline-none focus:ring-2 focus:ring-violet-300
                         disabled:border-gray-300 disabled:text-gray-400"
            >
              <Pencil size={16} aria-hidden="true" />
              Review &amp; Edit
            </button>

            <DownloadDocument
              documentId={documentId}
              documentFilename={documentFilename}
            />
            <p className="mt-3 text-xs text-gray-500">
              Preview, edit, or download in another format.
            </p>
          </div>
        ) : (
          <textarea
            value={translatedText}
            readOnly
            placeholder="Translation will appear here..."
            className="w-full min-h-0 flex-1 border rounded-xl p-4 resize-none
                       bg-gray-50"
          />
        )}
      </div>

      {isPreviewing && documentId && documentFilename && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center
                     bg-black/70 p-3 sm:p-6"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setIsPreviewing(false);
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-label={`Preview of ${documentFilename}`}
            className="flex h-[94vh] w-full max-w-[1600px] flex-col
                       overflow-hidden rounded-xl bg-white shadow-2xl"
          >
            <header className="flex min-h-14 items-center justify-between
                               gap-4 border-b px-4 py-3 sm:px-6">
              <h2 className="min-w-0 truncate text-base font-semibold
                             text-gray-800 sm:text-lg">
                {documentFilename}
              </h2>

              <div className="flex shrink-0 items-center gap-2">
                <a
                  href={`${API_BASE_URL}/review/download/${documentId}`}
                  className="inline-flex items-center gap-2 rounded-lg bg-violet-600
                             px-3 py-2 text-sm font-semibold text-white shadow-sm
                             transition hover:bg-violet-700 focus:outline-none
                             focus:ring-2 focus:ring-violet-300 focus:ring-offset-2"
                  title={`Download reconstructed ${documentFilename.split(".").pop()} file`}
                >
                  <Download size={18} aria-hidden="true" />
                  <span>
                    Download {documentFilename.split(".").pop()?.toUpperCase()}
                  </span>
                </a>

                <button
                  type="button"
                  onClick={() => setIsPreviewing(false)}
                  className="inline-flex items-center gap-2 rounded-lg
                             px-3 py-2 text-sm font-medium text-gray-700
                             hover:bg-gray-100"
                  aria-label="Close preview"
                >
                  <span className="hidden sm:inline">Close preview</span>
                  <X size={20} />
                </button>
              </div>
            </header>

            <iframe
              key={documentId}
              title={`Preview of ${documentFilename}`}
              src={`${API_BASE_URL}/review/preview/${documentId}#toolbar=0&navpanes=0`}
              className="min-h-0 w-full flex-1 bg-gray-100"
            />
          </section>
        </div>
      )}
    </>
  );
}

export default OutputPanel;
