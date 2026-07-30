import LanguageSelector from "../components/LanguageSelector";
import InputPanel from "../components/Input";
import OutputPanel from "../components/Output";

function Home() {
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        
        <LanguageSelector />

        {/* Input & Output Panels */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <InputPanel />
          <OutputPanel />
        </div>

      </div>
    </div>
  );
}

export default Home;