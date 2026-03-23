import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Results from "./pages/Results";
import Analyze from "./pages/Analyze";
import Report from "./pages/Report";
import Review from "./pages/Review";
import Blacklist from "./pages/Blacklist";
import Auth from "./pages/Auth";
import History from "./pages/History";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/report" element={<Report />} />
        <Route path="/review/:sellerId" element={<Review />} />
        <Route path="/blacklist" element={<Blacklist />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/history" element={<History />} />
      </Routes>
    </BrowserRouter>
  );
}
