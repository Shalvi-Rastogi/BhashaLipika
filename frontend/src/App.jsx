import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import ReviewDocument from "./pages/ReviewDocument";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/review" element={<ReviewDocument />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;