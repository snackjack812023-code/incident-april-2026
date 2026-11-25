"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/admin", label: "หน้าหลัก" },
  { href: "/admin/leaves", label: "การลา" },
  { href: "/admin/attendance", label: "ลงเวลา" },
  { href: "/admin/employees", label: "พนักงาน" },
  { href: "/admin/settings", label: "ตั้งค่า" },
] as const;

export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-3 pb-2">
      {LINKS.map((link) => {
        const active = link.href === "/admin" ? pathname === "/admin" : pathname.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${
              active ? "bg-line/10 text-line-dark" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
