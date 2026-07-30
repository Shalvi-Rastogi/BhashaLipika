import { useState, useRef } from "react";
import { Upload } from "lucide-react";

function InputPanel() {
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];

    if (file) {
      setSelectedFile(file);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-md p-6 h-[500px] flex flex-col">

      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-gray-700">
          Input
        </h2>

        <span className="text-sm text-gray-500">
          {text.length} / 5000
        </span>
      </div>

      {/* Text / Upload Buttons */}
      <div className="flex bg-gray-100 rounded-xl p-1 mb-5">

        <button
          onClick={() => setMode("text")}
          className={`flex-1 py-2 rounded-lg font-medium transition ${
            mode === "text"
              ? "bg-purple-600 text-white shadow"
              : "text-gray-600"
          }`}
        >
          Text
        </button>

        <button
          onClick={() => setMode("upload")}
          className={`flex-1 py-2 rounded-lg font-medium transition ${
            mode === "upload"
              ? "bg-purple-600 text-white shadow"
              : "text-gray-600"
          }`}
        >
          Upload
        </button>

      </div>

      {/* TEXT MODE */}
      {mode === "text" ? (

        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={5000}
          placeholder="Type or paste your text here..."
          className="flex-1 border border-gray-300 rounded-xl p-4 resize-none
                     focus:outline-none focus:ring-2 focus:ring-purple-500"
        />

      ) : (

        /* UPLOAD MODE */
        <div
          className="flex-1 border-2 border-dashed border-gray-300
                     rounded-xl flex flex-col items-center justify-center
                     text-center p-6"
        >

          <Upload
            size={45}
            className="text-purple-600 mb-4"
          />

          <h3 className="text-lg font-semibold text-gray-700">
            Drag & Drop your file
          </h3>

          <p className="text-gray-500 mt-2 mb-5">
            PDF, DOCX, PPTX, XLSX, RTF
          </p>

          {/* Hidden File Input */}
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.rtf"
            onChange={handleFileChange}
          />

          {/* Browse Button */}
          <button
            onClick={() => fileInputRef.current.click()}
            className="bg-purple-600 hover:bg-purple-700
                       text-white px-6 py-2 rounded-lg transition"
          >
            Browse Files
          </button>

          {/* Selected File Name */}
          {selectedFile && (
            <p className="mt-4 text-sm text-green-600 font-medium">
              Selected File:
              <br />
              {selectedFile.name}
            </p>
          )}

        </div>

      )}

    </div>
  );
}

export default InputPanel;