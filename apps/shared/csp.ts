const GOOGLE_FONTS_STYLES_ORIGIN = "https://fonts.googleapis.com";
const GOOGLE_FONTS_ASSETS_ORIGIN = "https://fonts.gstatic.com";
const GOOGLE_TAG_MANAGER_ORIGIN = "https://www.googletagmanager.com";
const GOOGLE_ANALYTICS_ORIGIN = "https://www.google-analytics.com";
const GOOGLE_ANALYTICS_REGION_ORIGIN = "https://region1.google-analytics.com";

const unique = <T>(values: T[]): T[] => Array.from(new Set(values));

export const extractAllowedOrigins = (values: Array<string | undefined>): string[] =>
  unique(
    values.flatMap((value) => {
      if (!value) {
        return [];
      }

      try {
        const url = new URL(value);
        if (url.protocol !== "http:" && url.protocol !== "https:") {
          return [];
        }
        return [url.origin];
      } catch {
        return [];
      }
    }),
  );

type BuildCspOptions = {
  apiBasePath?: string;
  publicApiBasePath?: string;
  siteUrl?: string;
  enableGoogleAnalytics?: boolean;
  isDevelopment?: boolean;
};

export const buildCspHeaderValue = ({
  apiBasePath,
  publicApiBasePath,
  siteUrl,
  enableGoogleAnalytics = false,
  isDevelopment = false,
}: BuildCspOptions): string => {
  const remoteOrigins = extractAllowedOrigins([apiBasePath, publicApiBasePath, siteUrl]);
  const scriptSrc = ["'self'", "'unsafe-inline'"];
  const styleSrc = ["'self'", "'unsafe-inline'", GOOGLE_FONTS_STYLES_ORIGIN];
  const fontSrc = ["'self'", "data:", GOOGLE_FONTS_ASSETS_ORIGIN];
  const imgSrc = ["'self'", "data:", "blob:", ...remoteOrigins];
  const connectSrc = ["'self'", ...remoteOrigins];

  if (isDevelopment) {
    scriptSrc.push("'unsafe-eval'");
  }

  if (enableGoogleAnalytics) {
    scriptSrc.push(GOOGLE_TAG_MANAGER_ORIGIN);
    connectSrc.push(GOOGLE_TAG_MANAGER_ORIGIN, GOOGLE_ANALYTICS_ORIGIN, GOOGLE_ANALYTICS_REGION_ORIGIN);
  }

  return [
    ["default-src", ["'self'"]],
    ["base-uri", ["'self'"]],
    ["object-src", ["'none'"]],
    ["frame-ancestors", ["'self'"]],
    ["script-src", unique(scriptSrc)],
    ["style-src", unique(styleSrc)],
    ["img-src", unique(imgSrc)],
    ["font-src", unique(fontSrc)],
    ["connect-src", unique(connectSrc)],
  ]
    .map(([directive, values]) => `${directive} ${values.join(" ")}`)
    .join("; ");
};
