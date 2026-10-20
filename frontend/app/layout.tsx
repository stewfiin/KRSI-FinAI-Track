import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { Navbar } from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FinAI Track — Smart Personal Finance & AI Assistant",
  description:
    "Asisten keuangan pribadi cerdas bertenaga AI dengan pencatatan suara, chat, dan automated budgeting adaptif.",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "FinAI Track",
  },
};

export const viewport: Viewport = {
  themeColor: "#0B0F19",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="dark">
      <body className={`${inter.className} min-h-screen bg-background text-slate-100 antialiased`}>
        <Providers>
          <Navbar />
          <main className="mx-auto max-w-5xl px-4 pt-4 pb-24 md:pl-56 md:pb-12">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}

