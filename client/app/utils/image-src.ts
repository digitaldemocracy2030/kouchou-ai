/**
 * 静的エクスポート時のベースパスを取得する
 * @returns ベースパス (例: "/path" または "")
 */
export const getBasePath = (): string => {
  const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
  const basePath = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";

  return isStaticExport ? basePath : "";
};

/**
 * パスを生成する
 * @param path パス (例: "/images/example.png")
 * @returns basePath付きのパス (例: "/path/images/example.png")
 */
export const getRelativeUrl = (path: string): string => {
  const basePath = getBasePath();

  // パスが / で始まることを確認し、先頭の / を除去
  const cleanPath = path.startsWith("/") ? path.substring(1) : path;

  // basePathとパスを結合
  return basePath ? `${basePath}/${cleanPath}` : `/${cleanPath}`;
};

/**
 * リモートアセットの完全なURLを取得する
 * サーバーやリモートから画像を取得する場合に使用
 *
 * @param path 画像のパス (例: "/images/example.png")
 * @param baseUrl ベースURL (例: "http://localhost:3000" or "http://192.168.1.100:3000")
 * @returns 完全なURL (例: "http://localhost:3000/images/example.png")
 */
export const getRemoteImageUrl = (path: string, baseUrl: string = process.env.NEXT_PUBLIC_SITE_URL || ""): string => {
  if (!path || !baseUrl) {
    return path; // フォールバック
  }

  try {
    const url = new URL(path, baseUrl);
    return url.toString();
  } catch {
    // URL構築に失敗した場合は相対パスを返す
    return path;
  }
};

/**
 * 静的アセット（public/内の画像など）のパスを取得
 * 絶対URLの場合はそのまま返し、相対パスの場合は環境に応じたベースパスを付与する
 * リモートHTTPアクセスの場合は完全なURLを生成する
 *
 * @param src 画像のパス (例: "/images/example.png" または "https://example.com/image.png")
 * @returns 適切に処理された画像のパス
 */
export const getImageFromServerSrc = (src: string): string => {
  // 空文字列の場合は早期リターン
  if (!src) return "";

  try {
    // 絶対URLの場合はそのまま返す（有効なURLかどうかを検証）
    new URL(src);
    return src;
  } catch (error) {
    // 相対パスの場合は静的アセット用のbasePathを使用
    return getRelativeUrl(src);
  }
};
