import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gold AI Trading Dashboard — XAU/USD",
  description: "Professional real-time market analysis and advisory dashboard for XAU/USD gold trading.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-[#09090b] text-[#fafafa] antialiased">
        {children}
      </body>
    </html>
  );
}
