import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { type ReactNode } from "react";

const DESKTOP_USER = {
  id: "desktop-user",
  name: "桌面用户",
  email: "desktop@hongtian.ai",
  role: "admin",
};

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="h-screen w-screen bg-[#060b14] flex flex-col overflow-hidden relative">
      {children}
    </div>
  );
}
