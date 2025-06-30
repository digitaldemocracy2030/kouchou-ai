import { Footer } from "@/components/Footer/Footer";
import { Toaster } from "@/components/ui/toaster";
import { GoogleAnalytics } from "@next/third-parties/google";
import type { Metadata } from "next";
import ClientProvider from "./ClientProvider";
import "./global.css";

export const metadata: Metadata = {
  title: "デジタル民主主義2030ブロードリスニング",
  robots: {
    index: false,
    follow: false,
  },
};

const enableGA =
  !!process.env.NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID &&
  (process.env.ENVIRONMENT === "production" || process.env.NODE_ENV === "production");

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html suppressHydrationWarning lang={"ja"}>
      <head>
        <link rel={"icon"} href={`${process.env.NEXT_PUBLIC_API_BASEPATH}/meta/icon.png`} sizes={"any"} />
        {enableGA && <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID || ""} />}
      </head>
      <body>
        <ClientProvider>
          {children}
          <Toaster />
          <Footer />
        </ClientProvider>
      </body>
    </html>
  );
}
