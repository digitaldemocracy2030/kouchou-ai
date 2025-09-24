import { getImageFromServerSrc } from "@/app/utils/image-src";
import { Provider } from "@/components/ui/provider";
import { GoogleAnalytics } from "@next/third-parties/google";
import "./global.css";

const enableGA =
  !!process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID &&
  (process.env.ENVIRONMENT === "production" || process.env.NODE_ENV === "production");

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html suppressHydrationWarning lang={"ja"}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=BIZ+UDPGothic&display=swap" rel="stylesheet" />

        <link rel={"icon"} href={getImageFromServerSrc("/meta/icon.png")} sizes={"any"} />

        {enableGA && <GoogleAnalytics gaId={process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || ""} />}
      </head>
      <body>
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
