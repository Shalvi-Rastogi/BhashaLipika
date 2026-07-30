function SaveToMemory() {
  return (
    <div className="bg-white rounded-xl shadow-md border p-5">
      <h3 className="text-lg font-semibold mb-2">
         Save to Memory
      </h3>

      <p className="text-gray-500 text-sm mb-4">
        Save this translation for future use.
      </p>

      <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg font-medium">
        Save to Memory
      </button>
    </div>
  );
}

export default SaveToMemory;