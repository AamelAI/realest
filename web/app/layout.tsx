import type { Metadata, Viewport } from "next";
import { Bricolage_Grotesque, Public_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  subsets: ["latin"], variable: "--font-bricolage", weight: ["500", "700", "800"],
});
const publicSans = Public_Sans({
  subsets: ["latin"], variable: "--font-public", weight: ["400", "500", "600"],
});
const jetbrains = JetBrains_Mono({
  subsets: ["latin"], variable: "--font-jetbrains", weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Realest — your shortlist",
  description: "Which listings are actually real.",
};

// Opened one-handed, mid-call. Never let it zoom-jump on input focus.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f4f1" },
    { media: "(prefers-color-scheme: dark)", color: "#0e100c" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${bricolage.variable} ${publicSans.variable} ${jetbrains.variable}`}>
      <body>{children}</body>
    </html>
  );
}
