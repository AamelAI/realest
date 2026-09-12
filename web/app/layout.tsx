import type { Metadata, Viewport } from "next";
import { Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

// Archivo: a grotesque with real width and a signage feel — deliberately not
// Inter, Geist or Space Grotesk. JetBrains Mono carries every figure and label.
const archivo = Archivo({
  subsets: ["latin"], variable: "--font-archivo", weight: ["400", "500", "600", "700"],
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin"], variable: "--font-jetbrains", weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Realest — your shortlist",
  description: "Which listings are actually real.",
};

// Opened one-handed, mid-call. Never let it zoom-jump.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#fcfcfb",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // Light by design. A verification record reads as a printed page, and one
    // committed ground lets the status colours work as text.
    <html lang="en" className={`${archivo.variable} ${jetbrains.variable}`} style={{ colorScheme: "light" }}>
      <body>{children}</body>
    </html>
  );
}
