import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import Shell from "./components/layout/Shell";
import Dashboard from "./pages/Dashboard";
import RatingBoard from "./pages/RatingBoard";
import Watchlist from "./pages/Watchlist";
import News from "./pages/News";
import StockDetail from "./pages/StockDetail";
import DailyReview from "./pages/DailyReview";
import ReviewHistory from "./pages/ReviewHistory";
import Strategies from "./pages/Strategies";
import Operations from "./pages/Operations";
import Settings from "./pages/Settings";
import TradingQuotes from "./pages/TradingQuotes";
import Placeholder from "./pages/Placeholder";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Dashboard />} />
            <Route path="ratings" element={<RatingBoard />} />
            <Route path="watchlist" element={<Watchlist />} />
            <Route path="news" element={<News />} />
            <Route path="review" element={<DailyReview />} />
            <Route path="review/history" element={<ReviewHistory />} />
            <Route path="strategies" element={<Strategies />} />
            <Route path="operations" element={<Operations />} />
            <Route path="quotes" element={<TradingQuotes />} />
            <Route path="stock/:code" element={<StockDetail />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Placeholder />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
