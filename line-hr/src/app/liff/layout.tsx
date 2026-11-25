import { DevBanner } from "@/components/liff/dev-banner";
import { LiffProvider } from "@/components/liff/liff-provider";

// LIFF endpoint URL in LINE Developers Console: https://<your-app>/liff
export default function LiffLayout({ children }: LayoutProps<"/liff">) {
  return (
    <LiffProvider>
      <div className="mx-auto min-h-screen max-w-md px-4 pb-12 pt-5">
        {children}
        <DevBanner />
      </div>
    </LiffProvider>
  );
}
