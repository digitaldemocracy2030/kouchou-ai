export const getApiBaseUrl = () => {
  // Standalone (Windows embeddable) is served same-origin by FastAPI, so use
  // root-relative requests and ignore NEXT_PUBLIC_API_BASEPATH (a dev .env.local
  // may point it elsewhere).
  if (process.env.NEXT_PUBLIC_STANDALONE === "1") {
    return "";
  }
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASEPATH;
  }
  // undefinedでなければAPI_BASEPATHを返す
  if (process.env.API_BASEPATH) {
    return process.env.API_BASEPATH;
  }
  return process.env.NEXT_PUBLIC_API_BASEPATH;
};
