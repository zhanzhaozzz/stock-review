import { useLocation } from "react-router-dom";

export default function Placeholder() {
  const location = useLocation();
  const pageName = location.pathname.replace(/^\//, "") || "home";

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="text-center">
        <div className="text-6xl mb-4">🚧</div>
        <h2 className="text-xl font-bold text-gray-300 mb-2">
          {pageName} 页面开发中
        </h2>
        <p className="text-gray-500">Sprint 2/3 将实现此功能</p>
      </div>
    </div>
  );
}
