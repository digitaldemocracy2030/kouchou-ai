export const getApiBaseUrl = () => {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASEPATH;
  }
  // undefinedでなければAPI_BASEPATHを返す
  if (process.env.API_BASEPATH) {
    return process.env.API_BASEPATH;
  }
  return process.env.NEXT_PUBLIC_API_BASEPATH;
};

// サーバー側（Route Handler / Server Action）で ADMIN_API_KEY が無いときの案内。
// NEXT_PUBLIC_ADMIN_API_KEY だけを設定した環境で起きやすいので、何を足せばよいかを書き添える。
export const ADMIN_API_KEY_MISSING_MESSAGE =
  "ADMIN_API_KEY is not set: admin のサーバー側の環境変数に ADMIN_API_KEY（NEXT_PUBLIC_ADMIN_API_KEY と同じ値）を設定してください";
