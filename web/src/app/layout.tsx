import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Used Vehicle IDSS",
  description:
    "Intelligent Decision Support System for used-vehicle acquisition: buy/pass, max price, and profitability.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="app-bg min-h-screen font-sans antialiased text-slate-900">
        {children}
      </body>
    </html>
  );
}
