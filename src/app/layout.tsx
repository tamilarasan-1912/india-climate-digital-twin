import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "India Climate Digital Twin",
  description: "India-focused climate intelligence and digital twin platform.",
};

// Do not use next/font/google here: production builds must be reproducible in
// offline or restricted CI environments. The console declares a local system
// font stack in CSS instead of making the build depend on a network fetch.
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
