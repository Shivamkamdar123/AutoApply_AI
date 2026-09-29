import type { Metadata } from "next";
import { Inter, Space_Grotesk, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  weight: ["400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-plex-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AutoApply AI — Autonomous Human-Supervised Job Application Agent",
  description:
    "An autonomous AI agent that matches, maps, and fills job applications with an unbreakable human-in-the-loop review queue and dry-run safety valve.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${spaceGrotesk.variable} ${ibmPlexMono.variable} dark`}
    >
      <body className="bg-base text-text-primary min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
