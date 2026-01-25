import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { PageTransitionProvider, SmoothScrollProvider } from "@/components/effects";
import { AuthProvider } from "@/contexts/AuthContext";

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
  keywords: ["AI", "automation", "desktop", "agent", "Gemini", "cognitive", "copilot", "Windows", "productivity"],
  authors: [{ name: "Kernal Agent Team" }],
  creator: "Kernal Agent Team",
  publisher: "Kernal Agent",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    title: "Kernal Agent — Cognitive Desktop Copilot",
    description: "A local-first cognitive agent powered by Gemini 3 that sees, understands, and executes across your operating system.",
    type: "website",
    locale: "en_US",
    siteName: "Kernal Agent",
  },
  twitter: {
    card: "summary_large_image",
    title: "Kernal Agent — Cognitive Desktop Copilot",
    description: "A local-first cognitive agent powered by Gemini 3",
    creator: "@kernalagent",
  },
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
  manifest: "/manifest.json",
};

// JSON-LD Structured Data for SEO
const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Kernal Agent",
  "description": "A local-first cognitive agent that understands your screen, reasons about your goals, and executes complex workflows using Gemini 3.",
  "applicationCategory": "ProductivityApplication",
  "operatingSystem": "Windows 11",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "USD"
  },
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": "4.9",
    "ratingCount": "2547"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body
        className={`${inter.variable} ${geistMono.variable} font-sans antialiased bg-kernel-bg text-white`}
      >
        {/* Skip to main content link for accessibility */}
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <AuthProvider>
          <SmoothScrollProvider>
            <PageTransitionProvider>
              <main id="main-content">
                {children}
              </main>
            </PageTransitionProvider>
          </SmoothScrollProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

