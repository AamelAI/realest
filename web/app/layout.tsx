import type { Metadata, Viewport } from "next";
import { Instrument_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Per the design handoff: Instrument Sans for UI, IBM Plex Mono for every
// figure, rank, clock and address in a machine context.
const instrument = Instrument_Sans({
  subsets: ["latin"], variable: "--font-instrument", weight: ["400", "500", "600", "700"],
});
const plex = IBM_Plex_Mono({
  subsets: ["latin"], variable: "--font-plex", weight: ["400", "500"],
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
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${instrument.variable} ${plex.variable}`} style={{ colorScheme: "light" }}>
      <body>{children}</body>
    </html>
  );
}
