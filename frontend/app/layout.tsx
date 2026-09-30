import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClintelAI — Your Trusted AI Healthcare Companion",
  description:
    "Multilingual, evidence-grounded healthcare intelligence, provider discovery, and verified health alerts platform.",
  keywords: [
    "Healthcare AI",
    "Evidence Grounded RAG",
    "Doctor Finder",
    "Health Alerts",
    "WHO ICMR MoHFW",
    "Multilingual Health",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-slate-50 text-slate-900 font-sans antialiased selection:bg-blue-100 selection:text-blue-900">
        {children}
      </body>
    </html>
  );
}
