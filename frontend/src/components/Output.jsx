// import { useState } from "react";
// import { Copy, Check } from "lucide-react";

// function OutputPanel({ translatedText }) {
//   const [copied, setCopied] = useState(false);

//   const handleCopy = async () => {
//     if (!translatedText?.trim()) return;

//     try {
//       await navigator.clipboard.writeText(translatedText);
//       setCopied(true);

//       setTimeout(() => {
//         setCopied(false);
//       }, 2000);
//     } catch (error) {
//       console.error("Failed to copy translated text:", error);
//     }
//   };

//   return (
//     <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">
//       <div className="flex items-center justify-between mb-4">
//         <h2 className="text-xl font-semibold">
//           Translated Text
//         </h2>

//         <button
//           type="button"
//           onClick={handleCopy}
//           disabled={!translatedText?.trim()}
//           title={copied ? "Copied!" : "Copy translation"}
//           aria-label="Copy translated text"
//           className="flex items-center gap-2 rounded-lg p-2
//                      text-gray-600 hover:bg-gray-100
//                      disabled:opacity-40 disabled:cursor-not-allowed
//                      transition-colors"
//         >
//           {copied ? (
//             <>
//               <Check size={18} className="text-green-600" />
//               <span className="text-sm text-green-600">
//                 Copied!
//               </span>
//             </>
//           ) : (
//             <>
//               <Copy size={18} />
//               <span className="text-sm">Copy</span>
//             </>
//           )}
//         </button>
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

// export default OutputPanel;
import { useState, useEffect } from "react";
import {
  Copy,
  Check,
  Volume2,
  VolumeX,
} from "lucide-react";

function OutputPanel({
  translatedText,
  targetLanguage = "hi",
}) {
  const [copied, setCopied] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  const handleCopy = async () => {
    if (!translatedText?.trim()) return;

    try {
      await navigator.clipboard.writeText(translatedText);
      setCopied(true);

      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error("Failed to copy translation:", error);
    }
  };

  const handleSpeak = () => {
    if (!translatedText?.trim()) return;

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

    const utterance = new SpeechSynthesisUtterance(
      translatedText
    );

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
    <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">
          Translated Text
        </h2>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSpeak}
            disabled={!translatedText?.trim()}
            title={speaking ? "Stop speaking" : "Listen to translation"}
            aria-label={speaking ? "Stop speaking" : "Listen to translation"}
            className="flex items-center gap-2 rounded-lg p-2
                       text-gray-600 hover:bg-gray-100
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
            disabled={!translatedText?.trim()}
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
      </div>

      <textarea
        value={translatedText || ""}
        readOnly
        placeholder="Translation will appear here..."
        className="w-full h-[340px] border rounded-xl p-4 resize-none
                   bg-gray-50"
      />
    </div>
  );
}

export default OutputPanel;