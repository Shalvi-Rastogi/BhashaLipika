// import { useLocation, useNavigate } from "react-router-dom";
// import { useState } from "react";
// import axios from "axios";

// const API_BASE_URL =
//   import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// function ReviewDocument() {
//   const location = useLocation();
//   const navigate = useNavigate();

//   const documentData = location.state?.documentData;

//   // Backend response structure:
//   // {
//   //   document_id: 45,
//   //   data: {
//   //      filename: "...",
//   //      sheets: [...]
//   //   }
//   // }

//   const documentId = documentData?.document_id;
//   const actualData = documentData?.data;

//   const [editedData, setEditedData] = useState(
//     actualData || null
//   );
//   const [isEditing, setIsEditing] = useState(false);
//   const [isSaving, setIsSaving] = useState(false);
//   const [isDownloading, setIsDownloading] = useState(false);

//   if (!documentData || !actualData) {
//     return (
//       <div className="min-h-screen bg-gray-100 p-8">
//         <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-md p-8">
//           <h1 className="text-2xl font-bold mb-4">
//             No Document Found
//           </h1>

//           <p className="text-gray-600 mb-6">
//             Please upload and translate a document first.
//           </p>

//           <button
//             type="button"
//             onClick={() => navigate("/")}
//             className="bg-violet-600 hover:bg-violet-700 text-white px-6 py-3 rounded-lg"
//           >
//             Go Back
//           </button>
//         </div>
//       </div>
//     );
//   }

//   const handleCellChange = (sheetIndex, cellIndex, value) => {
//     setEditedData((previousData) => {
//       const updatedData = {
//         ...previousData,
//         sheets: [...previousData.sheets],
//       };

//       updatedData.sheets[sheetIndex] = {
//         ...updatedData.sheets[sheetIndex],
//         cells: [...updatedData.sheets[sheetIndex].cells],
//       };

//       updatedData.sheets[sheetIndex].cells[cellIndex] = {
//         ...updatedData.sheets[sheetIndex].cells[cellIndex],
//         translated_text: value,
//       };

//       return updatedData;
//     });
//   };

//   // ---------------------------------------
//   // SAVE CHANGES
//   // ---------------------------------------
//  const handleSaveChanges = async () => {
//   try {
//     setIsSaving(true);

//     // Convert editedData into the format expected by backend
//     const edits = [];

//     editedData?.sheets?.forEach((sheet) => {
//       sheet.cells?.forEach((cell) => {
//         edits.push({
//           cell: cell.coordinate,
//           translated_text: cell.translated_text || "",
//         });
//       });
//     });

//     const response = await axios.post(
//       `${API_BASE_URL}/review/save`,
//       {
//         document_id: documentId,
//         edits: edits,
//       }
//     );

//     console.log("Save response:", response.data);

//     alert("Changes saved successfully!");

//   } catch (error) {
//     console.error("Save failed:", error);

//     alert(
//       error.response?.data?.detail ||
//       JSON.stringify(error.response?.data) ||
//       "Failed to save changes."
//     );
//   } finally {
//     setIsSaving(false);
//   }
// };
//   // ---------------------------------------
//   // DOWNLOAD FINAL DOCUMENT
//   // ---------------------------------------
//   const handleDownload = async () => {
//   try {
//     setIsDownloading(true);

//     // Convert editedData into backend edit format
//     const edits = [];

//     editedData?.sheets?.forEach((sheet) => {
//       sheet.cells?.forEach((cell) => {
//         edits.push({
//           cell: cell.coordinate,
//           translated_text: cell.translated_text || "",
//         });
//       });
//     });

//     // Save latest edits first
//     await axios.post(
//       `${API_BASE_URL}/review/save`,
//       {
//         document_id: documentId,
//         edits: edits,
//       }
//     );

//     // Then download updated document
//     const response = await axios.get(
//       `${API_BASE_URL}/review/download/${documentId}`,
//       {
//         responseType: "blob",
//       }
//     );

//     const blob = new Blob([response.data]);

//     const url = window.URL.createObjectURL(blob);

//     const link = document.createElement("a");
//     link.href = url;

//     link.download =
//       actualData.filename ||
//       documentData.filename ||
//       "translated_document.xlsx";

//     document.body.appendChild(link);
//     link.click();

//     link.remove();
//     window.URL.revokeObjectURL(url);

//   } catch (error) {
//     console.error("Download failed:", error);

//     alert(
//       error.response?.data?.detail ||
//       JSON.stringify(error.response?.data) ||
//       "Failed to download the document."
//     );
//   } finally {
//     setIsDownloading(false);
//   }
// };

//   return (
//     <div className="min-h-screen bg-gray-100 p-8">
//       <div className="max-w-7xl mx-auto">

//         {/* Header */}
//         <div className="mb-6">
//           <h1 className="text-3xl font-bold text-gray-800">
//             Review Translated Document
//           </h1>

//           <p className="text-gray-500 mt-2">
//             {actualData.filename}
//           </p>
//         </div>

//         {/* Sheets */}
//         {editedData?.sheets?.map((sheet, sheetIndex) => (
//           <div
//             key={sheetIndex}
//             className="bg-white rounded-2xl shadow-md p-6 mb-6"
//           >
//             <h2 className="text-xl font-semibold mb-5">
//               {sheet.sheet_name}
//             </h2>

//             <div className="overflow-x-auto">
//               <table className="w-full border-collapse">

//                 <thead>
//                   <tr className="bg-gray-100">
//                     <th className="border p-3 text-left">
//                       Cell
//                     </th>

//                     <th className="border p-3 text-left">
//                       Original Text
//                     </th>

//                     <th className="border p-3 text-left">
//                       Translated Text
//                     </th>
//                   </tr>
//                 </thead>

//                 <tbody>
//                   {sheet.cells?.map((cell, cellIndex) => (
//                     <tr key={cellIndex}>

//                       {/* Cell coordinate */}
//                       <td className="border p-3 font-semibold text-gray-700">
//                         {cell.coordinate}
//                       </td>

//                       {/* Original text */}
//                       <td className="border p-3 text-gray-700">
//                         {cell.original_text || ""}
//                       </td>

//                       {/* Editable translation */}
//                       <td className="border p-3">
//                         {isEditing ? (
//                             <textarea
//                             value={cell.translated_text || ""}
//                             onChange={(e) =>
//                                 handleCellChange(
//                                 sheetIndex,
//                                 cellIndex,
//                                 e.target.value
//                                 )
//                             }
//                             className="
//                                 w-full
//                                 min-h-[70px]
//                                 border
//                                 border-gray-300
//                                 rounded-lg
//                                 p-3
//                                 resize-y
//                                 focus:outline-none
//                                 focus:ring-2
//                                 focus:ring-violet-500
//                             "
//                             />
//                         ) : (
//                             <div className="min-h-[70px] p-3">
//                             {cell.translated_text || ""}
//                             </div>
//                         )}
//                         </td>

//                     </tr>
//                   ))}
//                 </tbody>

//               </table>
//             </div>
//           </div>
//         ))}

//         {/* Buttons */}
//         <div className="flex gap-4 mb-8">
//             {/* BACK TO HOME */}
//             <button
//                 type="button"
//                 onClick={() => {
//                     navigate("/", {
//                     state: {
//                         documentData: documentData,
//                         targetLanguage: location.state?.targetLanguage || "",
//                         inputText: location.state?.inputText || "",
//                     },
//                     });
//                 }}
//                 className="
//                     bg-gray-600
//                     hover:bg-gray-700
//                     text-white
//                     font-semibold
//                     px-6
//                     py-3
//                     rounded-lg
//                 "
//                 >
//                 Back
//             </button>

//           {/* SAVE */}
//           <button
//             type="button"
//             onClick={handleSaveChanges}
//             disabled={isSaving}
//             className="
//               bg-violet-600
//               hover:bg-violet-700
//               disabled:bg-gray-400
//               text-white
//               font-semibold
//               px-6
//               py-3
//               rounded-lg
//             "
//           >
//             {isSaving ? "Saving..." : "Save Changes"}
//           </button>

//           {/* DOWNLOAD */}
//           <button
//             type="button"
//             onClick={handleDownload}
//             disabled={isDownloading}
//             className="
//               bg-green-600
//               hover:bg-green-700
//               disabled:bg-gray-400
//               text-white
//               font-semibold
//               px-6
//               py-3
//               rounded-lg
//             "
//           >
//             {isDownloading
//               ? "Preparing Download..."
//               : "Download Final Document"}
//           </button>

//         </div>

//       </div>
//     </div>
//   );
// }

// export default ReviewDocument;
import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import axios from "axios";
import { ArrowLeft, Download, Pencil, Save } from "lucide-react";

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

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

const collectDocxReviewEntries = (translatedData, originalData) => {
  const entries = [];

  const addText = (path, translatedText, originalText, label) => {
    if (typeof translatedText !== "string") return;

    entries.push({
      path,
      translatedText,
      originalText: typeof originalText === "string" ? originalText : "",
      label,
    });
  };

  const visit = (translated, original, path, label) => {
    if (Array.isArray(translated)) {
      translated.forEach((item, index) =>
        visit(item, original?.[index], [...path, index], label)
      );
      return;
    }

    if (!translated || typeof translated !== "object") return;

    if (["paragraph", "heading", "list_item"].includes(translated.type)) {
      const runs = translated.runs || [];
      if (runs.length) {
        runs.forEach((run, runIndex) => {
          addText(
            [...path, "runs", runIndex, "text"],
            run.text,
            original?.runs?.[runIndex]?.text,
            translated.type.replace("_", " ")
          );
        });
      } else {
        addText(
          [...path, "text"],
          translated.text,
          original?.text,
          translated.type.replace("_", " ")
        );
      }
      return;
    }

    if (translated.type === "textbox") {
      (translated.paragraphs || []).forEach((text, index) => {
        addText(
          [...path, "paragraphs", index],
          text,
          original?.paragraphs?.[index],
          "Text box"
        );
      });
      return;
    }

    if (translated.type === "image_text") {
      const ocrDetails = translated.ocr_details || [];
      ocrDetails.forEach((item, index) => {
        addText(
          [...path, "ocr_details", index, "translated_text"],
          item.translated_text || "",
          original?.ocr_details?.[index]?.text,
          "Image text"
        );
      });
      if (!ocrDetails.length) {
        addText(
          [...path, "translated_text"],
          translated.translated_text || "",
          original?.text,
          "Image text"
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
          label
        );
      });
      return;
    }

    if (
      typeof translated.text === "string" &&
      !translated.paragraphs
    ) {
      addText([...path, "text"], translated.text, original?.text, label);
      return;
    }

    if (translated.paragraphs) {
      visit(translated.paragraphs, original?.paragraphs, [...path, "paragraphs"], "Table paragraph");
    }
    if (translated.rows) {
      visit(translated.rows, original?.rows, [...path, "rows"], "Table content");
    }
    if (translated.cells) {
      visit(translated.cells, original?.cells, [...path, "cells"], "Table content");
    }
    if (translated.nested_tables) {
      visit(
        translated.nested_tables,
        original?.nested_tables,
        [...path, "nested_tables"],
        "Nested table"
      );
    }
    if (translated.elements) {
      visit(translated.elements, original?.elements, [...path, "elements"], label);
    }
  };

  visit(
    translatedData?.elements || [],
    originalData?.elements || [],
    ["elements"],
    "Document text"
  );

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
  const isWordDocument = ["doc", "docx"].includes(fileType);
  const actualData = isWordDocument
    ? documentData?.translated_data
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
          <h1 className="text-2xl font-bold mb-4">
            No Document Found
          </h1>

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
  // HANDLE CELL EDIT
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

  const getDocxEdits = () =>
    collectDocxReviewEntries(editedData, documentData?.data).map((entry) => ({
      path: entry.path,
      translated_text: entry.translatedText,
    }));

  // ---------------------------------------
  // SAVE CHANGES
  // ---------------------------------------
  const handleSaveChanges = async () => {
    try {
      setIsSaving(true);

      const edits = getEdits();
      const imageEdits = getImageEdits();
      const docxEdits = getDocxEdits();

      const response = await axios.post(
        `${API_BASE_URL}/review/save`,
        {
          document_id: documentId,
          edits: edits,
          image_edits: imageEdits,
          docx_edits: docxEdits,
        }
      );

      console.log("Save response:", response.data);

      alert("Changes saved successfully!");

      // Exit editing mode after successful save
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

      // Save latest edits first
      const edits = getEdits();
      const imageEdits = getImageEdits();
      const docxEdits = getDocxEdits();

      await axios.post(
        `${API_BASE_URL}/review/save`,
        {
          document_id: documentId,
          edits: edits,
          image_edits: imageEdits,
          docx_edits: docxEdits,
        }
      );

      // Download updated document
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
    : isLegacyXls
      ? "xls"
      : "xlsx";
  const finalFilename =
    documentData.reconstructed_docx_file ||
    documentData.reconstructed_file ||
    actualData.filename ||
    documentData.filename ||
    `translated_document.${fileExtension}`;
  const docxReviewEntries = isWordDocument
    ? collectDocxReviewEntries(editedData, documentData?.data)
    : [];

  if (isWordDocument) {
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
                Word document review
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
                  disabled={!docxReviewEntries.length}
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
                {docxReviewEntries.length} text items
              </span>
            </div>

            <div className="divide-y divide-[#e6ebe8]">
              {docxReviewEntries.map((entry) => (
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
              {!docxReviewEntries.length && (
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