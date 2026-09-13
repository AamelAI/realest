import type { Metadata, Viewport } from "next";
import { Instrument_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Instrument Sans as the full variable font, so in-between weights (540, 580)
// render exactly. Loading the static 400/500/600/700 files instead would snap
// every one of them to 600 and make the whole page look heavier.
const instrument = Instrument_Sans({
  subsets: ["latin"],
  variable: "--font-instrument",
});

// Kept for one job only: a running clock. Money is set in the sans.
const plex = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-plex",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Realest — your shortlist",
  description: "Which listings are actually real.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // Pinch-zoom stays on — this is read one-handed, sometimes in bright light.
  viewportFit: "cover",
  themeColor: "#fbfaf9",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${instrument.variable} ${plex.variable}`} style={{ colorScheme: "light" }}>
      <body>{children}</body>
    </html>
  );
}
