import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { Navbar } from "@/components/Navbar";

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
  themeColor: "#F8F9FD",
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
    <html lang="id">
      <body className="font-sans min-h-screen bg-background text-espresso antialiased selection:bg-[#C8F526] selection:text-black">
        <Providers>
          <Navbar />
          <main className="mx-auto max-w-5xl px-4 pt-4 pb-28 md:pl-56 md:pb-12">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}

