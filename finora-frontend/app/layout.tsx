import type { Metadata } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { Plus_Jakarta_Sans } from "next/font/google";
import "@/styles/globals.css";
import { Providers } from "./providers";

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-heading",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Finora — AI Equities Intelligence for Global Investors",
  description:
    "Real-time AI financial analysis for 555+ global stocks. Built for NRI and expat investors.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/finora_icon.png", type: "image/png" },
    ],
    apple: "/finora_icon.png",
    shortcut: "/finora_icon.png",
  },
  openGraph: {
    title: "Finora — AI Equities Intelligence",
    description: "Real-time AI financial analysis for NRI and global investors.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} ${plusJakarta.variable} font-sans antialiased`}
      >
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
