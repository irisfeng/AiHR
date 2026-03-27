import type { Metadata } from "next";
import { IBM_Plex_Sans, Manrope } from "next/font/google";

import "./globals.css";

const headingFont = Manrope({
  subsets: ["latin"],
  variable: "--font-heading",
});

const bodyFont = IBM_Plex_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "AIHR Recruiting OS",
  description: "Standalone recruiting workspace rebuilt outside Frappe.",
};

export default function RootLayout(props: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className={`${headingFont.variable} ${bodyFont.variable}`}>{props.children}</body>
    </html>
  );
}
