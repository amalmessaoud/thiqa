import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Navbar from "./components/NavBar";
import Home from "./pages/Home";
import Results from "./pages/Results";
import Analyze from "./pages/Analyze";
import Report from "./pages/Report";
import Review from "./pages/Review";
import Blacklist from "./pages/Blacklist";
import Auth from "./pages/Auth";
import TextAnalyze from "./pages/TextAnalyze";
import SellerProfile from "./pages/SellerProfile";
import Profile from "./pages/Profile";

function Layout() {
  const location = useLocation();
  const hideNavbar = location.pathname === "/auth";

  return (
    <>
      {!hideNavbar && <Navbar />}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/text-analyze" element={<TextAnalyze />} />
        <Route path="/report" element={<Report />} />
        <Route path="/review" element={<Review />} />
        <Route path="/seller/:sellerUrl" element={<SellerProfile />} />
        <Route path="/blacklist" element={<Blacklist />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout />
    </BrowserRouter>
  );
}
