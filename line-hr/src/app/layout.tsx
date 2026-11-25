import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "LINE HR — ลงเวลาและขอลาผ่าน LINE",
  description: "ระบบเช็คชื่อเข้า-ออกงานและขอลาผ่าน LINE สำหรับร้านค้าและธุรกิจขนาดเล็ก",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#06c755",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" className="h-full antialiased">
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
