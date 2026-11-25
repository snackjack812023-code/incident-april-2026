import Link from "next/link";

const FEATURES = [
  { title: "ขอลาใน LINE", body: "พนักงานกรอกฟอร์มใน LINE หัวหน้าได้การ์ดแจ้งเตือนพร้อมปุ่มอนุมัติ / ปฏิเสธทันที" },
  { title: "เช็คชื่อด้วย GPS", body: "เช็คอิน-เอาท์ได้เฉพาะในรัศมีของสาขา คำนวณมาสาย / ออกก่อนเวลาให้อัตโนมัติ" },
  { title: "โควตาวันลา", body: "ตั้งประเภทการลาและจำนวนวันต่อปี ระบบกันลาเกินและลาซ้อนให้เอง รองรับลาครึ่งวัน" },
  { title: "แดชบอร์ดเจ้าของร้าน", body: "ดูว่าใครมา ใครสาย ใครลาวันนี้ และอนุมัติคำขอที่ค้างอยู่ได้จากมือถือ" },
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-10 px-5 py-14">
      <header className="space-y-4">
        <p className="inline-flex rounded-full bg-line/10 px-3 py-1 text-sm font-medium text-line-dark">LINE HR</p>
        <h1 className="text-3xl font-bold leading-tight sm:text-4xl">ระบบลงเวลาและขอลาผ่าน LINE</h1>
        <p className="text-lg text-slate-600">
          พนักงานใช้ผ่าน LINE ที่มีอยู่แล้ว ไม่ต้องติดตั้งแอปเพิ่ม เจ้าของร้านจัดการทุกอย่างได้จากมือถือ
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link href="/admin" className="rounded-xl bg-line px-5 py-3 font-semibold text-white hover:bg-line-dark">
            เข้าสู่หน้าแอดมิน
          </Link>
          <Link href="/liff" className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-semibold hover:bg-slate-50">
            หน้าพนักงาน (LIFF)
          </Link>
        </div>
      </header>
      <section className="grid gap-4 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
            <h2 className="font-semibold">{f.title}</h2>
            <p className="mt-1 text-sm text-slate-600">{f.body}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
