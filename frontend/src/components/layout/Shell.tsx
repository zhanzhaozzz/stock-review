import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Shell() {
  return (
    <div className="min-h-screen bg-base text-primary">
      <Sidebar />
      <main className="ml-56 min-h-screen">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
