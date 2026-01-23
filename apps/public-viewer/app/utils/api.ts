/**
 * 実行環境に応じた適切なAPIのベースURLを取得する
 *
 * クライアントサイドではNEXT_PUBLIC_API_BASEPATHを使用し、
 * サーバーサイドではAPI_BASEPATHが設定されていればそれを使用する
 *
 * @returns APIのベースURL
 */
export const getApiBaseUrl = (): string => {
  // クライアントサイド（ブラウザ環境）の場合
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_BASEPATH || "";
  }

  // サーバーサイドでAPI_BASEPATHが設定されている場合
  if (process.env.API_BASEPATH) {
    return process.env.API_BASEPATH;
  }

  // それ以外の場合はNEXT_PUBLIC_API_BASEPATHを使用
  return process.env.NEXT_PUBLIC_API_BASEPATH || "";
};
