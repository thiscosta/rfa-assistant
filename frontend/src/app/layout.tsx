import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { ClaudeStatus } from "@/components/layout/ClaudeStatus";

export const metadata: Metadata = {
  title: "RFA Assistant",
  description: "Turn referral letters, intake forms, notes and cards into a completed Request for Approval of Services.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex h-14 max-w-[1500px] items-center gap-6 px-4">
            <Link href="/" className="font-semibold text-ink">
              RFA Assistant
            </Link>
            <nav className="flex gap-4 text-sm text-slate-600">
              <Link href="/" className="hover:text-ink">
                Requests
              </Link>
              <Link href="/settings" className="hover:text-ink">
                Clinic settings
              </Link>
            </nav>
            <div className="ml-auto">
              <ClaudeStatus />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1500px] px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
