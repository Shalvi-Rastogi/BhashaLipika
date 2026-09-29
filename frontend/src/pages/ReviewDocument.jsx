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

const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function ReviewDocument() {
  const location = useLocation();
  const navigate = useNavigate();

  const documentData = location.state?.documentData;

  const documentId = documentData?.document_id;
  const actualData = documentData?.data;

  const [editedData, setEditedData] = useState(actualData || null);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

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

  // ---------------------------------------
  // CONVERT DATA TO BACKEND EDIT FORMAT
  // ---------------------------------------
  const getEdits = () => {
    const edits = [];

    editedData?.sheets?.forEach((sheet) => {
      sheet.cells?.forEach((cell) => {
        edits.push({
          cell: cell.coordinate,
          translated_text: cell.translated_text || "",
        });
      });
    });

    return edits;
  };

  // ---------------------------------------
  // SAVE CHANGES
  // ---------------------------------------
  const handleSaveChanges = async () => {
    try {
      setIsSaving(true);

      const edits = getEdits();

      const response = await axios.post(
        `${API_BASE_URL}/review/save`,
        {
          document_id: documentId,
          edits: edits,
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

      await axios.post(
        `${API_BASE_URL}/review/save`,
        {
          document_id: documentId,
          edits: edits,
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

      link.download =
        actualData.filename ||
        documentData.filename ||
        "translated_document.xlsx";

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

  return (
    <div className="min-h-screen bg-gray-100 p-8">

      <div className="max-w-7xl mx-auto">

        {/* HEADER */}
        <div className="mb-6">

          <h1 className="text-3xl font-bold text-gray-800">
            Review Translated Document
          </h1>

          <p className="text-gray-500 mt-2">
            {actualData.filename}
          </p>

          <p className="text-sm text-gray-500 mt-1">
            Review and edit the translated content before downloading.
          </p>

        </div>


        {/* DOCUMENT PREVIEW */}
        {editedData?.sheets?.map((sheet, sheetIndex) => (

          <div
            key={sheetIndex}
            className="bg-white rounded-2xl shadow-md p-6 mb-6"
          >

            <h2 className="text-xl font-semibold mb-5">
              {sheet.sheet_name}
            </h2>

            <div className="overflow-x-auto">

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

                  {sheet.cells?.map((cell, cellIndex) => (

                    <tr key={cellIndex}>

                      {/* CELL */}
                      <td className="border p-3 font-semibold text-gray-700">
                        {cell.coordinate}
                      </td>


                      {/* ORIGINAL */}
                      <td className="border p-3 text-gray-700">
                        {cell.original_text || ""}
                      </td>


                      {/* TRANSLATED */}
                      <td className="border p-3">

                        {isEditing ? (

                          <textarea
                            value={cell.translated_text || ""}
                            onChange={(e) =>
                              handleCellChange(
                                sheetIndex,
                                cellIndex,
                                e.target.value
                              )
                            }
                            className="
                              w-full
                              min-h-[80px]
                              border
                              border-violet-400
                              rounded-lg
                              p-3
                              resize-y
                              bg-white
                              text-gray-800
                              focus:outline-none
                              focus:ring-2
                              focus:ring-violet-500
                            "
                          />

                        ) : (

                          <div
                            className="
                              w-full
                              min-h-[80px]
                              p-3
                              bg-gray-50
                              rounded-lg
                              text-gray-800
                              whitespace-pre-wrap
                            "
                          >
                            {cell.translated_text || ""}
                          </div>

                        )}

                      </td>

                    </tr>

                  ))}

                </tbody>

              </table>

            </div>

          </div>

        ))}


        {/* BUTTONS */}
        <div className="flex flex-wrap gap-4 mb-8">

          {/* BACK */}
          <button
            type="button"
            onClick={handleBack}
            className="
              bg-gray-600
              hover:bg-gray-700
              text-white
              font-semibold
              px-6
              py-3
              rounded-lg
            "
          >
            Back
          </button>


          {/* EDIT */}
          {!isEditing && (
            <button
              type="button"
              onClick={() => setIsEditing(true)}
              className="
                bg-blue-600
                hover:bg-blue-700
                text-white
                font-semibold
                px-6
                py-3
                rounded-lg
              "
            >
              Edit Document
            </button>
          )}


          {/* SAVE */}
          {isEditing && (
            <button
              type="button"
              onClick={handleSaveChanges}
              disabled={isSaving}
              className="
                bg-violet-600
                hover:bg-violet-700
                disabled:bg-gray-400
                text-white
                font-semibold
                px-6
                py-3
                rounded-lg
              "
            >
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          )}


          {/* DOWNLOAD */}
          <button
            type="button"
            onClick={handleDownload}
            disabled={isDownloading}
            className="
              bg-green-600
              hover:bg-green-700
              disabled:bg-gray-400
              text-white
              font-semibold
              px-6
              py-3
              rounded-lg
            "
          >
            {isDownloading
              ? "Preparing Download..."
              : "Download Final Document"}
          </button>

        </div>

      </div>

    </div>
  );
}

export default ReviewDocument;