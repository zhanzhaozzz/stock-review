import { BrowserRouter, Routes, Route } from "react-router-dom";
import Shell from "./components/layout/Shell";
import Dashboard from "./pages/Dashboard";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<Dashboard />} />
          <Route path="ratings" element={<Placeholder />} />
          <Route path="watchlist" element={<Placeholder />} />
          <Route path="news" element={<Placeholder />} />
          <Route path="review" element={<Placeholder />} />
          <Route path="review/history" element={<Placeholder />} />
          <Route path="strategies" element={<Placeholder />} />
          <Route path="operations" element={<Placeholder />} />
          <Route path="stock/:code" element={<Placeholder />} />
          <Route path="settings" element={<Placeholder />} />
          <Route path="*" element={<Placeholder />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
