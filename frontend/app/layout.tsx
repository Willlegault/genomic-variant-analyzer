import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import VantaBackground from "./components/VantaBackground";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Genomic Variant Analyzer",
  description:
    "Detect, classify, and interpret DNA variants against a reference CDS using Biopython + ClinVar.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-ink text-fg">
        <VantaBackground />
        <div aria-hidden className="scrim pointer-events-none fixed inset-0 -z-[5]" />
        {children}
      </body>
    </html>
  );
}
