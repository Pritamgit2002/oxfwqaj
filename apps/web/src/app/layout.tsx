import type { Metadata } from "next";
import { Suspense } from "react";

import { DataStatus } from "@/components/data-status";

import { NavLinks } from "@/components/nav-links";

import "./globals.css";

export const metadata: Metadata = {
  title: "Windsight · Day-ahead wind forecasts",
  description:
    "Latest national wind generation forecasts at the day-ahead decision time, and how accurate they are.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en-GB">
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <div className="flex items-baseline gap-3">
              <span className="text-lg font-semibold tracking-tight">Windsight</span>
              <span className="hidden text-sm text-muted sm:inline">
                GB day-ahead wind position · pilot January 2026
              </span>
            </div>
            <div className="flex items-center gap-3">
              <Suspense fallback={null}>
                <DataStatus />
              </Suspense>
              <NavLinks />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">{children}</main>
        <footer className="mx-auto max-w-7xl px-4 pb-8 text-xs text-muted sm:px-6">
          Data: Elexon BMRS — FUELHH (wind outturn) and WINDFOR (national wind forecast). Times
          shown in UK local time.
        </footer>
      </body>
    </html>
  );
}
