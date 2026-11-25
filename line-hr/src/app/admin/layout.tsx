import Link from "next/link";
import { Suspense } from "react";
import { AdminNav } from "@/components/admin/nav";
import { AdminUser } from "@/components/admin/admin-user";

export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
          <Link href="/admin" className="text-lg font-bold">
            LINE HR <span className="text-line">Admin</span>
          </Link>
          <Suspense fallback={<span className="h-9 w-32 animate-pulse rounded-lg bg-slate-100" />}>
            <AdminUser />
          </Suspense>
        </div>
        <AdminNav />
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}
