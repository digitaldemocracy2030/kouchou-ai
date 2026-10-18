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
 * 静的アセット（public/内の画像など）のパスを取得
 * 絶対URLの場合はそのまま返し、相対パスの場合は環境に応じたベースパスを付与する
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

/**
 * metadata の相対 URL（og:image など）を絶対 URL にするための metadataBase を返す
 * NEXT_PUBLIC_SITE_URL（ホスト部分）に静的エクスポート時のベースパスを付けたもの。
 * 静的エクスポートで NEXT_PUBLIC_SITE_URL が未設定のときは警告して undefined を返す
 * （Next は http://localhost:3000 にフォールバックするので、SNS では画像が表示されない）。
 *
 * metadataBase にベースパスを含めるので、metadata に渡すパスにはベースパスを付けないこと
 * （Next は metadataBase のパスとつなげて解決する）。
 */
export const getMetadataBase = (): URL | undefined => {
  const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL || "").replace(/\/+$/, "");
  if (siteUrl) {
    return new URL(siteUrl + getBasePath());
  }
  if (process.env.NEXT_PUBLIC_OUTPUT_MODE === "export") {
    console.warn(
      "NEXT_PUBLIC_SITE_URL が未設定のため、静的HTML出力の og:image などが絶対 URL になりません。公開先の URL を設定してください。",
    );
    return undefined;
  }
  // 開発環境やSSR時の既定値
  return new URL(`http://localhost:3000${getBasePath()}`);
};
