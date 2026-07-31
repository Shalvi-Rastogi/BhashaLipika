function OutputPanel() {
  return (
    <div className="bg-white rounded-2xl shadow-md p-6 h-[450px]">

      <h2 className="text-xl font-semibold mb-4">
        Translated Text
      </h2>

      <textarea
        readOnly
        placeholder="Translation will appear here..."
        className="w-full h-[340px] border rounded-xl p-4 resize-none
                   bg-gray-50"
      />

    </div>
  );
}

export default OutputPanel;