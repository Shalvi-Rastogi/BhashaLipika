import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import axios from "axios";
import { ArrowLeft, Download, Pencil, Save } from "lucide-react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const getCellPosition = (cell) => {
  const coordinate = String(cell.coordinate || "");
  const match = coordinate.match(/^([A-Z]+)(\d+)$/i);

  if (!match) return null;

  let column = 0;
  for (const character of match[1].toUpperCase()) {
    column = column * 26 + character.charCodeAt(0) - 64;
  }

  return {
    row: Number(cell.row) || Number(match[2]),
    column: Number(cell.column) || column,
  };
};

const getColumnLabel = (columnNumber) => {
  let label = "";
  let remaining = columnNumber;

  while (remaining > 0) {
    const digit = (remaining - 1) % 26;
    label = String.fromCharCode(65 + digit) + label;
    remaining = Math.floor((remaining - 1) / 26);
  }

  return label;
};

const collectDocumentReviewEntries = (translatedData, originalData) => {
  const entries = [];

  const addText = (path, translatedText, originalText, label, position) => {
    if (typeof translatedText !== "string") return;
    entries.push({
      path,
      translatedText,
      originalText: typeof originalText === "string" ? originalText : "",
      label,
      _position: position,
    });
  };

  const addImageText = (path, translatedText, originalText, label, position) => {
    const hasText = [translatedText, originalText].some(
      (text) => typeof text === "string" && text.trim().length > 0
    );
    if (hasText) {
      addText(path, translatedText, originalText, label, position);
    }
  };

  // 1. PDF FORMAT HANDLING
  if (translatedData?.pages && Array.isArray(translatedData.pages)) {
    translatedData.pages.forEach((page, pIdx) => {
      const pageLabel = `Page ${page.page_number || pIdx + 1}`;
      const pageEntriesStart = entries.length;
      const getPosition = (bbox) =>
        Array.isArray(bbox) && Number.isFinite(Number(bbox[1]))
          ? Number(bbox[1])
          : Number.MAX_SAFE_INTEGER;
      
      // PDF Elements (Text Blocks & Tables)
      (page.elements || []).forEach((el, elIdx) => {
        if (el.type === "text") {
          addText(
            ["pages", pIdx, "elements", elIdx, "translated_text"],
            el.translated_text,
            el.original_text,
            `${pageLabel} - Text Block`,
            getPosition(el.bbox)
          );
        } else if (el.type === "table") {
          (el.rows || []).forEach((row, rIdx) => {
            (row.cells || []).forEach((cell, cIdx) => {
              const origCell = originalData?.pages?.[pIdx]?.elements?.[elIdx]?.rows?.[rIdx]?.cells?.[cIdx]?.original_text || cell.original_text || "";
              addText(
                ["pages", pIdx, "elements", elIdx, "rows", rIdx, "cells", cIdx, "translated_text"],
                cell.translated_text,
                origCell,
                `${pageLabel} - Table (R${rIdx + 1}C${cIdx + 1})`,
                getPosition(cell.bbox || el.bbox)
              );
            });
          });
        }
      });

      // PDF Images (OCR)
      (page.images || []).forEach((img, imgIdx) => {
        (img.ocr_data || []).forEach((ocrItem, ocrIdx) => {
          const origOcrText = originalData?.pages?.[pIdx]?.images?.[imgIdx]?.ocr_data?.[ocrIdx]?.text || ocrItem.text || "";
          addImageText(
            ["pages", pIdx, "images", imgIdx, "ocr_data", ocrIdx, "translated_text"],
            ocrItem.translated_text,
            origOcrText,
            `${pageLabel} - Image Text`,
            getPosition(img.bbox)
          );
        });
      });

      const orderedPageEntries = entries
        .slice(pageEntriesStart)
        .sort((left, right) => left._position - right._position);
      entries.splice(pageEntriesStart, orderedPageEntries.length, ...orderedPageEntries);
    });
    entries.forEach((entry) => delete entry._position);
    return entries;
  }

  // 2. DOCX & PPTX HANDLING
  const visit = (
    translated,
    original,
    path,
    label,
    inheritedPosition = Number.MAX_SAFE_INTEGER
  ) => {
    if (Array.isArray(translated)) {
      translated.forEach((item, index) =>
        visit(item, original?.[index], [...path, index], label, inheritedPosition)
      );
      return;
    }

    if (!translated || typeof translated !== "object") return;

    const typeStr = translated.type?.toLowerCase() || "";
    const reviewPosition = Number.isFinite(translated.review_order)
      ? translated.review_order
      : inheritedPosition;

    // PPTX SPECIFIC TYPES
    if (typeStr === "text_frame") {
      const slideNum = translated.slide_number ? `Slide ${translated.slide_number}` : label;
      addText(
        [...path, "translated_text"], 
        translated.translated_text, 
        original?.text || original?.original_text, 
        `${slideNum} - Text`
      );
      return;
    }

    if (typeStr === "table" && Array.isArray(translated.translated_data)) {
      const slideNum = translated.slide_number ? `Slide ${translated.slide_number}` : label;
      translated.translated_data.forEach((row, rIdx) => {
        if (Array.isArray(row)) {
          row.forEach((cellText, cIdx) => {
             const origCell = original?.translated_data?.[rIdx]?.[cIdx] || original?.data?.[rIdx]?.[cIdx] || "";
             addText(
               [...path, "translated_data", rIdx, cIdx],
               cellText,
               origCell,
               `${slideNum} - Table (R${rIdx + 1}C${cIdx + 1})`
             );
          });
        }
      });
      return;
    }

    if (typeStr === "image" && Array.isArray(translated.ocr_data)) {
      const slideNum = translated.slide_number ? `Slide ${translated.slide_number}` : label;
      translated.ocr_data.forEach((item, ocrIdx) => {
        addImageText(
          [...path, "ocr_data", ocrIdx, "translated_text"],
          item.translated_text || "",
          original?.ocr_data?.[ocrIdx]?.text || "",
          `${slideNum} - Image Text`
        );
      });
      if (!translated.ocr_data.length && translated.translated_text) {
        addImageText(
          [...path, "translated_text"],
          translated.translated_text,
          original?.text || "",
          `${slideNum} - Image Text`
        );
      }
      return;
    }

    if (["paragraph", "heading", "list_item"].includes(typeStr)) {
      const textPath = [...path, "text"];
      const translatedText =
        typeof translated.text === "string"
          ? translated.text
          : typeof translated.translated_text === "string"
            ? translated.translated_text
            : Array.isArray(translated.runs)
              ? translated.runs.map((run) => run.text || "").join("")
              : translated.original_text;
      const originalText =
        typeof original?.text === "string"
          ? original.text
          : typeof original?.original_text === "string"
            ? original.original_text
            : Array.isArray(original?.runs)
              ? original.runs.map((run) => run.text || "").join("")
              : "";

      addText(
        textPath,
        translatedText,
        originalText,
        typeStr.replace(/_/g, " "),
        reviewPosition
      );
      return;
    }

    // DOCX SPECIFIC TYPES
    if (["slide_text", "table_cell"].includes(typeStr)) {
      let displayLabel = translated.type.replace(/_/g, " ");
      if (translated.slide_number) {
        displayLabel = `Slide ${translated.slide_number} - ${displayLabel}`;
      }
      addText([...path, "text"], translated.text, original?.text, displayLabel);
      return;
    }

    if (typeStr === "textbox") {
      let displayLabel = "Text box";
      if (translated.slide_number) {
        displayLabel = `Slide ${translated.slide_number} - ${displayLabel}`;
      }
      (translated.paragraphs || []).forEach((text, index) => {
        addText(
          [...path, "paragraphs", index],
          text,
          original?.paragraphs?.[index],
          displayLabel,
          reviewPosition
        );
      });
      return;
    }

    if (typeStr === "image_text") {
      let displayLabel = "Image text";
      if (translated.slide_number) {
        displayLabel = `Slide ${translated.slide_number} - ${displayLabel}`;
      }
      const ocrDetails = translated.ocr_details || [];
      ocrDetails.forEach((item, index) => {
        addImageText(
          [...path, "ocr_details", index, "translated_text"],
          item.translated_text || "",
          original?.ocr_details?.[index]?.text,
          displayLabel,
          reviewPosition
        );
      });
      if (!ocrDetails.length) {
        addImageText(
          [...path, "translated_text"],
          translated.translated_text || "",
          original?.text,
          displayLabel,
          reviewPosition
        );
      }
      return;
    }

    if (Array.isArray(translated.runs)) {
      translated.runs.forEach((run, runIndex) => {
        addText(
          [...path, "runs", runIndex, "text"],
          run.text,
          original?.runs?.[runIndex]?.text,
          label,
          reviewPosition
        );
      });
      return;
    }

    if (typeof translated.text === "string" && !translated.paragraphs) {
      addText([...path, "text"], translated.text, original?.text, label, reviewPosition);
      return;
    }

    if (translated.paragraphs) {
      visit(
        translated.paragraphs,
        original?.paragraphs,
        [...path, "paragraphs"],
        "Table paragraph",
        reviewPosition
      );
    }
    if (translated.rows) {
      visit(translated.rows, original?.rows, [...path, "rows"], "Table content", reviewPosition);
    }
    if (translated.cells) {
      visit(translated.cells, original?.cells, [...path, "cells"], "Table content", reviewPosition);
    }
    if (translated.nested_tables) {
      visit(
        translated.nested_tables,
        original?.nested_tables,
        [...path, "nested_tables"],
        "Nested table",
        reviewPosition
      );
    }
    if (translated.elements) {
      visit(translated.elements, original?.elements, [...path, "elements"], label, reviewPosition);
    }
  };

  if (translatedData?.elements) {
    visit(translatedData.elements, originalData?.elements || [], ["elements"], "Document text");
    if (translatedData.document_type === "docx") {
      entries.sort((left, right) => left._position - right._position);
      entries.forEach((entry) => delete entry._position);
    }
  } else {
    Object.keys(translatedData || {}).forEach((key) => {
      if (key.startsWith("slide_")) {
        const slideNum = key.split('_')[1];
        visit(
          translatedData[key], 
          originalData?.[key] || [], 
          [key], 
          `Slide ${slideNum}`
        );
      }
    });
  }

  return entries;
};

const updateAtPath = (value, path, nextValue) => {
  if (!path.length) return nextValue;

  const [key, ...remainingPath] = path;
  const updated = Array.isArray(value) ? [...value] : { ...value };
  updated[key] = updateAtPath(value[key], remainingPath, nextValue);
  return updated;
};

function ReviewDocument() {
  const location = useLocation();
  const navigate = useNavigate();

  const documentData = location.state?.documentData;

  const documentId = documentData?.document_id;
  const fileType = documentData?.file_type?.toLowerCase();
  
  const isWordDocument = ["doc", "docx", "rtf"].includes(fileType);
  const isPowerPointDocument = ["ppt", "pptx"].includes(fileType);
  const isPdfDocument = ["pdf"].includes(fileType); // NAYA: PDF check
  const isDocumentView = isWordDocument || isPowerPointDocument || isPdfDocument; // NAYA: PDF added to document view

  const actualData = isDocumentView
    ? documentData?.translated_data || documentData?.data
    : documentData?.data;

  const [editedData, setEditedData] = useState(actualData || null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);

  const handleDocxTextChange = (path, value) => {
    setEditedData((previousData) => updateAtPath(previousData, path, value));
  };

  if (!documentData || !actualData) {
    return (
      <div className="min-h-screen bg-gray-100 p-8">
        <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-md p-8">
          <h1 className="text-2xl font-bold mb-4">No Document Found</h1>
          <p className="text-gray-600 mb-6">
            Please upload and translate a document first.
          </p>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="bg-violet-600 hover:bg-violet-700 text-white px-6 py-3 rounded-lg"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // ---------------------------------------
  // HANDLE CELL EDIT (Excel)
  // ---------------------------------------
  const handleCellChange = (sheetIndex, cellIndex, value) => {
    setEditedData((previousData) => {
      const updatedData = {
        ...previousData,
        sheets: [...previousData.sheets],
      };

      updatedData.sheets[sheetIndex] = {
        ...updatedData.sheets[sheetIndex],
        cells: [...updatedData.sheets[sheetIndex].cells],
      };

      updatedData.sheets[sheetIndex].cells[cellIndex] = {
        ...updatedData.sheets[sheetIndex].cells[cellIndex],
        translated_text: value,
      };

      return updatedData;
    });
  };

  const handleImageTextChange = (
    sheetIndex,
    imageIndex,
    ocrIndex,
    value
  ) => {
    setEditedData((previousData) => {
      const updatedData = { ...previousData, sheets: [...previousData.sheets] };
      const sheet = { ...updatedData.sheets[sheetIndex] };
      const images = [...(sheet.images || [])];
      const image = { ...images[imageIndex] };
      const ocrData = [...(image.ocr_data || [])];

      ocrData[ocrIndex] = {
        ...ocrData[ocrIndex],
        translated_text: value,
      };
      image.ocr_data = ocrData;
      image.translated_text = ocrData
        .map((item) => item.translated_text || "")
        .join("\n");
      images[imageIndex] = image;
      sheet.images = images;
      updatedData.sheets[sheetIndex] = sheet;

      return updatedData;
    });
  };

  // ---------------------------------------
  // CONVERT DATA TO BACKEND EDIT FORMAT
  // ---------------------------------------
  const getEdits = () => {
    return (editedData?.sheets?.[0]?.cells || []).map((cell) => ({
      cell: cell.coordinate,
      translated_text: cell.translated_text || "",
    }));
  };

  const getImageEdits = () =>
    (editedData?.sheets || []).flatMap((sheet, sheetIndex) =>
      (sheet.images || []).flatMap((image, imageIndex) =>
        (image.ocr_data || []).map((item, ocrIndex) => ({
          sheet_index: sheetIndex,
          image_index: imageIndex,
          ocr_index: ocrIndex,
          translated_text: item.translated_text || "",
        }))
      )
    );

  const getDocEdits = () =>
    collectDocumentReviewEntries(editedData, documentData?.data).map((entry) => ({
      path: entry.path,
      translated_text: entry.translatedText,
    }));

  // ---------------------------------------
  // SAVE CHANGES
  // ---------------------------------------
  const handleSaveChanges = async () => {
    try {
      setIsSaving(true);

      const editsPayload = { document_id: documentId };
      
      // Update logic to send edits to appropriate keys based on filetype
      if (isDocumentView) {
        editsPayload.docx_edits = getDocEdits(); 
        editsPayload.pptx_edits = getDocEdits(); 
        editsPayload.pdf_edits = getDocEdits(); // NAYA: PDF edits included
      } else {
        editsPayload.edits = getEdits();
        editsPayload.image_edits = getImageEdits();
      }

      const response = await axios.post(
        `${API_BASE_URL}/review/save`,
        editsPayload
      );

      console.log("Save response:", response.data);
      alert("Changes saved successfully!");
      setIsEditing(false);
    } catch (error) {
      console.error("Save failed:", error);
      alert(
        error.response?.data?.detail ||
          JSON.stringify(error.response?.data) ||
          "Failed to save changes."
      );
    } finally {
      setIsSaving(false);
    }
  };

  // ---------------------------------------
  // DOWNLOAD FINAL DOCUMENT
  // ---------------------------------------
  const handleDownload = async () => {
    try {
      setIsDownloading(true);

      const editsPayload = { document_id: documentId };
      if (isDocumentView) {
        editsPayload.docx_edits = getDocEdits(); 
        editsPayload.pptx_edits = getDocEdits(); 
        editsPayload.pdf_edits = getDocEdits();
      } else {
        editsPayload.edits = getEdits();
        editsPayload.image_edits = getImageEdits();
      }

      await axios.post(
        `${API_BASE_URL}/review/save`,
        editsPayload
      );

      const response = await axios.get(
        `${API_BASE_URL}/review/download/${documentId}`,
        {
          responseType: "blob",
        }
      );

      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = finalFilename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
      alert(
        error.response?.data?.detail ||
          JSON.stringify(error.response?.data) ||
          "Failed to download the document."
      );
    } finally {
      setIsDownloading(false);
    }
  };

  // ---------------------------------------
  // BACK TO HOME
  // ---------------------------------------
  const handleBack = () => {
    navigate("/", {
      state: {
        documentData: documentData,
        targetLanguage: location.state?.targetLanguage || "",
        inputText: location.state?.inputText || "",
        translatedText: location.state?.translatedText || "",
      },
    });
  };

  const sheets = editedData?.sheets || [];
  const activeSheet = sheets[activeSheetIndex];
  const positionedCells = (activeSheet?.cells || [])
    .map((cell, cellIndex) => ({
      ...getCellPosition(cell),
      cell,
      cellIndex,
    }))
    .filter((entry) => entry.row && entry.column);
  const visibleRows = [...new Set(positionedCells.map((entry) => entry.row))]
    .sort((left, right) => left - right);
  const visibleColumns = [...new Set(positionedCells.map((entry) => entry.column))]
    .sort((left, right) => left - right);
  const cellsByPosition = new Map(
    positionedCells.map((entry) => [`${entry.row}:${entry.column}`, entry])
  );
  const canEditActiveSheet = activeSheetIndex === 0;
  const canEditActiveContent =
    canEditActiveSheet || (activeSheet?.images || []).length > 0;
  
  const isLegacyXls =
    documentData.file_type?.toLowerCase() === "xls" ||
    /\.xls$/i.test(documentData.filename || "");
    
  const fileExtension = isWordDocument
    ? fileType
    : isPowerPointDocument
    ? fileType
    : isPdfDocument
    ? fileType
    : isLegacyXls
      ? "xls"
      : "xlsx";
      
  const finalFilename =
    documentData.reconstructed_pptx_file ||
    documentData.reconstructed_rtf_file ||
    documentData.reconstructed_docx_file ||
    documentData.reconstructed_pdf_file ||
    documentData.reconstructed_file ||
    actualData.filename ||
    documentData.filename ||
    `translated_document.${fileExtension}`;
    
  const documentReviewEntries = isDocumentView
    ? collectDocumentReviewEntries(editedData, documentData?.data)
    : [];

  // ==========================================================
  // WORD, PPTX & PDF UI
  // ==========================================================
  if (isDocumentView) {
    return (
      <main className="min-h-screen bg-[#f4f6f5] px-4 py-6 text-[#202a27] sm:px-8">
        <div className="mx-auto max-w-5xl">
          <header className="mb-5 flex flex-wrap items-end justify-between gap-4 border-b border-[#d8dfdc] pb-5">
            <div>
              <button
                type="button"
                onClick={handleBack}
                className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-[#53645d] hover:text-[#16734f]"
              >
                <ArrowLeft size={16} aria-hidden="true" /> Back
              </button>
              <h1 className="text-2xl font-semibold text-[#202a27]">
                {isPowerPointDocument
                  ? "Presentation review"
                  : isPdfDocument
                    ? "PDF Document review"
                    : fileType === "rtf"
                      ? "RTF document review"
                      : "Word document review"}
              </h1>
              <p className="mt-1 text-sm text-[#64716c]">
                {documentData.filename}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {!isEditing ? (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  disabled={!documentReviewEntries.length}
                  className="inline-flex items-center gap-2 rounded border border-[#16734f] bg-[#16734f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#105b3e] disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
                >
                  <Pencil size={16} aria-hidden="true" /> Edit document
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSaveChanges}
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 rounded border border-[#16734f] bg-[#16734f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#105b3e] disabled:cursor-wait disabled:bg-gray-400"
                >
                  <Save size={16} aria-hidden="true" />
                  {isSaving ? "Saving..." : "Save changes"}
                </button>
              )}
              <button
                type="button"
                onClick={handleDownload}
                disabled={isDownloading}
                className="inline-flex items-center gap-2 rounded border border-[#bbc8c2] bg-white px-4 py-2.5 text-sm font-semibold text-[#26362f] hover:bg-[#edf2ef] disabled:cursor-wait disabled:text-gray-400"
              >
                <Download size={16} aria-hidden="true" />
                {isDownloading ? "Preparing file..." : `Download .${fileExtension}`}
              </button>
            </div>
          </header>

          <section className="overflow-hidden rounded border border-[#cbd5d0] bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-[#dce3df] bg-[#f8faf9] px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="rounded-sm bg-[#e3eee8] px-2 py-1 text-xs font-semibold uppercase text-[#16734f]">
                  {fileExtension}
                </span>
                <span className="truncate text-sm font-medium text-[#394840]">
                  {documentData.filename}
                </span>
              </div>
              <span className="ml-3 shrink-0 text-xs text-[#78857f]">
                {documentReviewEntries.length} text items
              </span>
            </div>

            <div className="divide-y divide-[#e6ebe8]">
              {documentReviewEntries.map((entry) => (
                <article
                  key={entry.path.join(".")}
                  className="grid gap-3 px-4 py-4 sm:grid-cols-[130px_minmax(0,1fr)_minmax(0,1fr)] sm:px-6"
                >
                  <span className="text-xs font-semibold uppercase text-[#78857f]">
                    {entry.label}
                  </span>
                  <div>
                    <p className="mb-1 text-xs font-semibold text-[#87918c]">
                      Original
                    </p>
                    <p className="whitespace-pre-wrap break-words text-sm leading-6 text-[#596860]">
                      {entry.originalText || " "}
                    </p>
                  </div>
                  <div>
                    <label
                      htmlFor={`docx-review-${entry.path.join("-")}`}
                      className="mb-1 block text-xs font-semibold text-[#16734f]"
                    >
                      Translated
                    </label>
                    {isEditing ? (
                      <textarea
                        id={`docx-review-${entry.path.join("-")}`}
                        value={entry.translatedText}
                        onChange={(event) =>
                          handleDocxTextChange(entry.path, event.target.value)
                        }
                        rows={Math.min(
                          6,
                          Math.max(2, entry.translatedText.split("\n").length)
                        )}
                        className="w-full resize-y rounded-sm border border-[#cbd5d0] px-3 py-2 text-sm leading-6 text-[#202a27] outline-none focus:border-[#35a276] focus:ring-2 focus:ring-[#35a276]/20"
                      />
                    ) : (
                      <p className="whitespace-pre-wrap break-words text-sm leading-6 text-[#202a27]">
                        {entry.translatedText || " "}
                      </p>
                    )}
                  </div>
                </article>
              ))}
              {!documentReviewEntries.length && (
                <p className="px-6 py-12 text-center text-sm text-[#78857f]">
                  No reviewable text was found in this document.
                </p>
              )}
            </div>
          </section>
        </div>
      </main>
    );
  }

  // ==========================================================
  // EXCEL UI
  // ==========================================================
  return (
    <main className="min-h-screen bg-[#f4f6f5] px-4 py-6 text-[#202a27] sm:px-8">
      <div className="mx-auto max-w-[1440px]">
        <header className="mb-5 flex flex-wrap items-end justify-between gap-4 border-b border-[#d8dfdc] pb-5">
          <div>
            <button
              type="button"
              onClick={handleBack}
              className="mb-3 inline-flex items-center gap-2 text-sm font-medium text-[#53645d] hover:text-[#16734f]"
            >
              <ArrowLeft size={16} aria-hidden="true" /> Back
            </button>
            <h1 className="text-2xl font-semibold tracking-normal text-[#202a27]">
              Workbook review
            </h1>
            <p className="mt-1 text-sm text-[#64716c]">
              {documentData.filename || actualData.filename}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {!isEditing ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                disabled={!canEditActiveContent}
                className="inline-flex items-center gap-2 rounded border border-[#16734f] bg-[#16734f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#105b3e] disabled:cursor-not-allowed disabled:border-gray-300 disabled:bg-gray-200 disabled:text-gray-500"
              >
                <Pencil size={16} aria-hidden="true" /> Edit sheet
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSaveChanges}
                disabled={isSaving}
                className="inline-flex items-center gap-2 rounded border border-[#16734f] bg-[#16734f] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#105b3e] disabled:cursor-wait disabled:bg-gray-400"
              >
                <Save size={16} aria-hidden="true" />
                {isSaving ? "Saving..." : "Save changes"}
              </button>
            )}
            <button
              type="button"
              onClick={handleDownload}
              disabled={isDownloading}
              className="inline-flex items-center gap-2 rounded border border-[#bbc8c2] bg-white px-4 py-2.5 text-sm font-semibold text-[#26362f] hover:bg-[#edf2ef] disabled:cursor-wait disabled:text-gray-400"
            >
              <Download size={16} aria-hidden="true" />
              {isDownloading
                ? `Preparing .${fileExtension}...`
                : `Download .${fileExtension}`}
            </button>
          </div>
        </header>

        <section className="overflow-hidden rounded border border-[#cbd5d0] bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-[#dce3df] bg-[#f8faf9] px-4 py-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="shrink-0 rounded-sm bg-[#e3eee8] px-2 py-1 text-xs font-semibold uppercase text-[#16734f]">
                {fileExtension.toUpperCase()}
              </span>
              <span className="truncate text-sm font-medium text-[#394840]">
                {documentData.filename || actualData.filename}
              </span>
            </div>
            {activeSheet && (
              <span className="ml-3 shrink-0 text-xs text-[#78857f]">
                {positionedCells.length} populated cells
              </span>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full table-fixed border-collapse text-left">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 w-14 border border-[#d7dfdb] bg-[#edf1ef] px-2 py-2 text-center text-xs font-medium text-[#65726c]" />
                  {visibleColumns.map((column) => (
                    <th
                      key={column}
                      className="min-w-[220px] border border-[#d7dfdb] bg-[#edf1ef] px-3 py-2 text-center text-xs font-semibold text-[#596860]"
                    >
                      {getColumnLabel(column)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row) => (
                  <tr key={row}>
                    <th className="sticky left-0 z-[1] w-14 border border-[#d7dfdb] bg-[#f4f6f5] px-2 py-2 text-center text-xs font-medium text-[#65726c]">
                      {row}
                    </th>
                    {visibleColumns.map((column) => {
                      const entry = cellsByPosition.get(`${row}:${column}`);

                      return (
                        <td
                          key={column}
                          className="h-28 min-w-[220px] border border-[#d7dfdb] bg-white p-0 align-top"
                        >
                          {entry && (
                            <div className="flex h-full min-h-28 flex-col">
                              {isEditing && canEditActiveSheet ? (
                                <textarea
                                  aria-label={`Translated content for ${entry.cell.coordinate}`}
                                  value={entry.cell.translated_text || ""}
                                  onChange={(event) =>
                                    handleCellChange(
                                      activeSheetIndex,
                                      entry.cellIndex,
                                      event.target.value
                                    )
                                  }
                                  className="min-h-[72px] w-full flex-1 resize-y border-0 bg-[#fbfdfb] px-3 py-2 text-sm leading-5 text-[#202a27] outline-none focus:bg-white focus:ring-2 focus:ring-inset focus:ring-[#35a276]"
                                />
                              ) : (
                                <div className="min-h-[72px] flex-1 whitespace-pre-wrap break-words px-3 py-2 text-sm leading-5 text-[#202a27]">
                                  {entry.cell.translated_text || ""}
                                </div>
                              )}
                              <div className="truncate border-t border-[#edf1ef] bg-[#fafbfa] px-3 py-1.5 text-xs text-[#87918c]" title={entry.cell.original_text || ""}>
                                {entry.cell.original_text || " "}
                              </div>
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
                {!positionedCells.length && (
                  <tr>
                    <td colSpan={Math.max(visibleColumns.length + 1, 1)} className="px-6 py-12 text-center text-sm text-[#78857f]">
                      {activeSheet?.images?.length
                        ? "This worksheet contains embedded image text; review it below."
                        : "This worksheet has no translated cells."}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {(activeSheet?.images || []).length > 0 && (
            <section className="border-t border-[#d7dfdb] bg-[#f8faf9] p-4 sm:p-6">
              <h2 className="mb-4 text-base font-semibold text-[#26362f]">
                Embedded image text
              </h2>
              <div className="space-y-4">
                {activeSheet.images.map((image, imageIndex) => (
                  <article
                    key={`${image.image_index ?? imageIndex}-${image.row}-${image.column}`}
                    className="overflow-hidden rounded border border-[#d7dfdb] bg-white"
                  >
                    <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[#e5ebe7] px-4 py-3">
                      <h3 className="text-sm font-semibold text-[#394840]">
                        Image {imageIndex + 1}
                      </h3>
                      {image.row && image.column && (
                        <span className="text-xs text-[#78857f]">
                          {getColumnLabel(image.column)}{image.row}
                        </span>
                      )}
                    </header>

                    {image.ocr_data?.length ? (
                      <div className="divide-y divide-[#edf1ef]">
                        {image.ocr_data.map((item, ocrIndex) => (
                          <div
                            key={`${item.text}-${ocrIndex}`}
                            className="grid gap-3 p-4 md:grid-cols-2"
                          >
                            <div>
                              <p className="mb-1 text-xs font-semibold uppercase text-[#78857f]">
                                Original
                              </p>
                              <p className="whitespace-pre-wrap break-words text-sm text-[#596860]">
                                {item.text || ""}
                              </p>
                            </div>
                            <div>
                              <label
                                htmlFor={`image-${activeSheetIndex}-${imageIndex}-${ocrIndex}`}
                                className="mb-1 block text-xs font-semibold uppercase text-[#16734f]"
                              >
                                Translated
                              </label>
                              {isEditing ? (
                                <textarea
                                  id={`image-${activeSheetIndex}-${imageIndex}-${ocrIndex}`}
                                  value={item.translated_text || ""}
                                  onChange={(event) =>
                                    handleImageTextChange(
                                      activeSheetIndex,
                                      imageIndex,
                                      ocrIndex,
                                      event.target.value
                                    )
                                  }
                                  rows={2}
                                  className="w-full resize-y rounded-sm border border-[#cbd5d0] px-3 py-2 text-sm text-[#202a27] outline-none focus:border-[#35a276] focus:ring-2 focus:ring-[#35a276]/20"
                                />
                              ) : (
                                <p className="whitespace-pre-wrap break-words text-sm text-[#202a27]">
                                  {item.translated_text || ""}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="px-4 py-5 text-sm text-[#78857f]">
                        {image.original_text || "No text was detected in this image."}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            </section>
          )}

          <nav aria-label="Workbook sheets" className="flex min-h-12 items-end gap-1 overflow-x-auto border-t border-[#d7dfdb] bg-[#f4f6f5] px-3 pt-2">
            {sheets.map((sheet, sheetIndex) => (
              <button
                key={`${sheet.sheet_name}-${sheetIndex}`}
                type="button"
                onClick={() => {
                  setActiveSheetIndex(sheetIndex);
                  setIsEditing(false);
                }}
                aria-current={activeSheetIndex === sheetIndex ? "page" : undefined}
                className={`max-w-56 truncate border-x border-t px-4 py-2 text-sm ${
                  activeSheetIndex === sheetIndex
                    ? "border-[#d7dfdb] border-b-white bg-white font-semibold text-[#16734f]"
                    : "border-transparent text-[#68766f] hover:bg-[#e9eeeb]"
                }`}
              >
                {sheet.sheet_name || `Sheet ${sheetIndex + 1}`}
              </button>
            ))}
          </nav>
        </section>
      </div>
    </main>
  );
}

export default ReviewDocument;