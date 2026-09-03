import { useState, useRef, useEffect } from "react";
import { Upload } from "lucide-react";
import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const MAX_DOCX_FILE_SIZE = 5 * 1024 * 1024;

function InputPanel({ resetKey , targetLanguage}) {
  const [mode, setMode] = useState("text");
  const [text, setText] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  const fileInputRef = useRef(null);

  // Reset input whenever resetKey changes
  useEffect(() => {
    setText("");
    setSelectedFile(null);
    setMode("text");
    setUploadStatus("");
    setIsUploading(false);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [resetKey]);

  const handleFileChange = async (e) => {
    const file = e.target.files[0];

    if (!file) return;

    if (
      file.name.toLowerCase().endsWith(".docx") &&
      file.size > MAX_DOCX_FILE_SIZE
    ) {
      setSelectedFile(null);
      setUploadStatus("Upload failed.");
      e.target.value = "";
      alert("Only files up to 5 MB can be handled.");
      return;
    }

    setSelectedFile(file);
    setUploadStatus("Uploading and processing...");
    setIsUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("target_language", targetLanguage);

    try {
      const response = await axios.post(
        `${API_BASE_URL}/upload`,
        formData,
        {
          timeout: 600000,
        }
      );

      console.log("Backend Response:", response.data);

      setUploadStatus("Completed successfully!");

      alert(
        response.data.message ||
          "File uploaded and processed successfully!"
      );
    } catch (error) {
      console.error("Upload failed:", error);

      setUploadStatus("Upload failed.");

      if (error.code === "ECONNABORTED") {
        alert(
          "Processing is taking too long. Please check the backend."
        );
      } else {
        alert(
          error.response?.data?.detail ||
            "Upload or processing failed."
        );
      }
    } finally {
      setIsUploading(false);
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
            <br />
            DOCX files up to 5 MB
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
            disabled={isUploading}
            className={`text-white px-6 py-2 rounded-lg transition ${
              isUploading
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-purple-600 hover:bg-purple-700"
            }`}
          >
            {isUploading ? "Processing..." : "Browse Files"}
          </button>

          {/* Selected File Name */}
          {selectedFile && (
            <p className="mt-4 text-sm text-green-600 font-medium">
              Selected File:
              <br />
              {selectedFile.name}
            </p>
          )}

          {/* Upload Status */}
          {uploadStatus && (
            <p
              className={`mt-3 text-sm font-medium ${
                uploadStatus === "Upload failed."
                  ? "text-red-600"
                  : uploadStatus === "Completed successfully!"
                  ? "text-green-600"
                  : "text-purple-600"
              }`}
            >
              {uploadStatus}
            </p>
          )}

        </div>

      )}

    </div>
  );
}

export default InputPanel;