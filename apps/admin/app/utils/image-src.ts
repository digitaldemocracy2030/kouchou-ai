/**
 * 静的アセット（public/ 配下の画像など）のパスを返す。
 *
 * standalone(static export) では basePath(/admin-ui)配下に配信されるため、Chakra の
 * <Image src> など next が basePath を自動付与しない参照には手動でプレフィックスが要る。
 * ホスト版では NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH が空なので従来どおり。
 */
export const getStaticAssetPath = (path: string): string => {
  const basePath = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";
  const clean = path.startsWith("/") ? path : `/${path}`;
  return `${basePath}${clean}`;
};
