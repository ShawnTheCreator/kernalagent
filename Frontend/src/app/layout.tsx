import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { PageTransitionProvider } from "@/components/effects/PageTransition";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kernal Agent — Cognitive Desktop Copilot",
  description: "A local-first cognitive agent that understands your screen, reasons about your goals, and executes complex workflows using Gemini 3.",
  keywords: ["AI", "automation", "desktop", "agent", "Gemini", "cognitive"],
  authors: [{ name: "Kernal Agent Team" }],
  openGraph: {
    title: "Kernal Agent — Cognitive Desktop Copilot",
    description: "A local-first cognitive agent powered by Gemini 3",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${geistMono.variable} font-sans antialiased bg-kernel-bg text-white`}
      >
        <PageTransitionProvider>
          {children}
        </PageTransitionProvider>
      </body>
    </html>
  );
}

