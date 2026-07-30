function DownloadDocument() {
  return (
    <div className="bg-white rounded-xl shadow-md border p-5">
      <h3 className="text-lg font-semibold mb-2">
         Download Document
      </h3>

      <p className="text-gray-500 text-sm mb-4">
        Download the translated document in the same format.
      </p>

      <button
        className="
          bg-green-600
          hover:bg-green-700
          text-white
          px-5
          py-2
          rounded-lg
          font-medium
          transition
        "
      >
        Download
      </button>
    </div>
  );
}

export default DownloadDocument;