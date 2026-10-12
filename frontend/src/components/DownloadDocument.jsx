import { useEffect, useState } from "react";
import axios from "axios";
import { Download } from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function DownloadDocument({
  documentId,
  documentFilename,
  onDownload,
  isDownloading = false,
  compact = false,
}) {
  const [formats, setFormats] = useState([]);
  const [selectedFormat, setSelectedFormat] = useState("");
  const [isLoadingFormats, setIsLoadingFormats] = useState(Boolean(documentId));
  const [error, setError] = useState("");

  useEffect(() => {
    let isCurrent = true;

    const loadFormats = async () => {
      setIsLoadingFormats(true);
      setError("");

      try {
        const response = await axios.get(
          `${API_BASE_URL}/review/download-formats/${documentId}`
        );
        if (!isCurrent) return;

        const availableFormats = response.data.formats || [];
        const defaultFormat =
          response.data.default_format ||
          availableFormats.find(
            (format) => format.extension === response.data.current_format
          )?.extension ||
          availableFormats[0]?.extension ||
          "";

        setFormats(availableFormats);
        setSelectedFormat(defaultFormat);
      } catch (requestError) {
        if (!isCurrent) return;
        setError(
          requestError.response?.data?.detail ||
            "Could not load available download formats."
        );
      } finally {
        if (isCurrent) setIsLoadingFormats(false);
      }
    };

    if (documentId) loadFormats();

    return () => {
      isCurrent = false;
    };
  }, [documentId]);

  const handleDownload = async () => {
    if (!selectedFormat) return;
    setError("");

    try {
      if (onDownload) {
        await onDownload(selectedFormat);
        return;
      }

      const response = await axios.get(
        `${API_BASE_URL}/review/download/${documentId}`,
        {
          params: { format: selectedFormat },
          responseType: "blob",
        }
      );
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement("a");
      const stem = documentFilename.replace(/\.[^.]+$/, "");
      link.href = url;
      link.download = `${stem}.${selectedFormat}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (requestError) {
      let message =
        requestError.response?.data?.detail ||
        requestError.response?.data?.message;
      if (requestError.response?.data instanceof Blob) {
        try {
          const responseBody = JSON.parse(
            await requestError.response.data.text()
          );
          message = responseBody.detail || responseBody.message;
        } catch {
          message = "";
        }
      }
      setError(message || "Failed to download the document.");
    }
  };

  const select = (
    <select
      value={selectedFormat}
      onChange={(event) => setSelectedFormat(event.target.value)}
      disabled={isLoadingFormats || !formats.length || isDownloading}
      className={`w-full rounded-lg border border-gray-300 bg-white text-sm text-gray-800
                  outline-none transition focus:border-violet-500 focus:ring-2
                  focus:ring-violet-100 disabled:cursor-wait disabled:bg-gray-100
                  ${compact ? "px-2.5 py-2" : "px-3 py-2.5"}`}
      aria-label="Download format"
    >
      {isLoadingFormats && <option value="">Loading formats...</option>}
      {!isLoadingFormats && !formats.length && (
        <option value="">No formats available</option>
      )}
      {formats.map((format) => (
        <option key={format.extension} value={format.extension}>
          {format.label}
        </option>
      ))}
    </select>
  );

  return (
    <div className={compact
      ? "flex flex-wrap items-center gap-2"
      : "mt-5 flex w-full flex-col items-center gap-3 sm:flex-row sm:justify-center"}>
      {!compact && (
        <label className="flex w-full items-center gap-3 text-sm font-medium text-gray-700 sm:w-auto">
          <span className="shrink-0">Download format</span>
          <span className="min-w-0 flex-1 sm:w-64 sm:flex-none">{select}</span>
        </label>
      )}
      {compact && <label className="sr-only">{select}</label>}
      <button
        type="button"
        onClick={handleDownload}
        disabled={isLoadingFormats || !selectedFormat || isDownloading}
        className={`inline-flex w-full items-center justify-center gap-2 rounded-lg
                    font-semibold text-white shadow-sm transition
                    focus:outline-none focus:ring-2 focus:ring-violet-300
                    focus:ring-offset-2 disabled:cursor-wait disabled:bg-gray-400
                    sm:w-auto
                    ${compact
                      ? "bg-violet-600 px-3 py-2 text-sm hover:bg-violet-700"
                      : "bg-green-600 px-5 py-2.5 hover:bg-green-700"}`}
      >
        <Download size={compact ? 16 : 18} aria-hidden="true" />
        {isDownloading ? "Preparing file..." : "Download"}
      </button>
      {error && (
        <p className="w-full text-center text-sm text-red-600 sm:text-left" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export default DownloadDocument;
