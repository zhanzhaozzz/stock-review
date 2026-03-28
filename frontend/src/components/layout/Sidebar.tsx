import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "市场总览", icon: "📊" },
  { to: "/ratings", label: "量化评级", icon: "📈" },
  { to: "/watchlist", label: "自选股", icon: "⭐" },
  { to: "/news", label: "新闻聚合", icon: "📰" },
  { to: "/review", label: "每日复盘", icon: "📝" },
  { to: "/review/history", label: "历史复盘", icon: "📅" },
  { to: "/strategies", label: "战法库", icon: "🎯" },
  { to: "/operations", label: "操作记录", icon: "📋" },
  { to: "/settings", label: "设置", icon: "⚙️" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 h-screen bg-gray-900 border-r border-gray-800 flex flex-col fixed left-0 top-0">
      <div className="px-5 py-5 border-b border-gray-800">
        <h1 className="text-lg font-bold text-white">Stock Review</h1>
        <p className="text-xs text-gray-500 mt-1">每日复盘系统</p>
      </div>
      <nav className="flex-1 py-3 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-gray-800 text-white border-r-2 border-blue-500"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
