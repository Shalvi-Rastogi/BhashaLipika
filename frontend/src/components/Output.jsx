import { Download, Eye, FileText, Pencil, X } from "lucide-react";
import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function OutputPanel({
  translatedText,
  documentFilename,
  documentId,
  onReviewDocument,
}) {
  const [isPreviewing, setIsPreviewing] = useState(false);
  const fileExtension = documentFilename?.split(".").pop()?.toUpperCase();

  useEffect(() => {
    if (!isPreviewing) return undefined;

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsPreviewing(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isPreviewing]);

  return (
    <>
      <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">
        <h2 className="text-xl font-semibold mb-4">
          {documentFilename ? "Translated Document" : "Translated Text"}
        </h2>

        {documentFilename ? (
          <div className="h-[340px] border rounded-xl bg-gray-50 p-4 flex flex-col items-center justify-center text-center">
            <FileText size={48} className="text-violet-600 mb-4" />
            <p className="text-sm text-gray-500 mb-3">
              Your reconstructed translation is ready.
            </p>
            <button
              type="button"
              onClick={() => setIsPreviewing(true)}
              disabled={!documentId}
              className="max-w-full inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-3 font-semibold text-white transition hover:bg-violet-700 disabled:cursor-not-allowed disabled:bg-gray-400"
              title={`Preview ${documentFilename}`}
            >
              <span className="min-w-0 truncate">{documentFilename}</span>
              <Eye size={18} className="shrink-0" />
            </button>
            <button
              type="button"
              onClick={onReviewDocument}
              disabled={!documentId}
              className="mt-4 inline-flex items-center gap-2 rounded-lg border border-violet-600 px-4 py-2 font-semibold text-violet-700 transition hover:bg-violet-50 disabled:cursor-not-allowed disabled:border-gray-300 disabled:text-gray-400"
            >
              <Pencil size={16} />
              Review &amp; Edit (HITL)
            </button>
            <p className="text-xs text-gray-500 mt-3">
              Preview the reconstructed file or open it for human review and editing.
            </p>
          </div>
        ) : (
          <textarea
            value={translatedText}
            readOnly
            placeholder="Translation will appear here..."
            className="w-full h-[340px] border rounded-xl p-4 resize-none
                       bg-gray-50"
          />
        )}
      </div>

      {isPreviewing && documentId && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-3 sm:p-6"
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
            className="flex h-[94vh] w-full max-w-[1600px] flex-col overflow-hidden rounded-xl bg-white shadow-2xl"
          >
            <header className="flex min-h-14 items-center justify-between gap-4 border-b px-4 py-3 sm:px-6">
              <h2 className="min-w-0 truncate text-base font-semibold text-gray-800 sm:text-lg">
                {documentFilename}
              </h2>
              <div className="flex shrink-0 items-center gap-2">
                <a
                  href={`${API_BASE_URL}/review/download/${documentId}`}
                  className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-violet-700"
                  title={`Download reconstructed ${fileExtension} file`}
                >
                  <Download size={18} />
                  <span>Download {fileExtension}</span>
                </a>
                <button
                  type="button"
                  onClick={() => setIsPreviewing(false)}
                  className="inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100"
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