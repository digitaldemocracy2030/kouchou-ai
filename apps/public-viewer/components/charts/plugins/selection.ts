type Mode = { id: string; isDisabled: boolean };

/** modes は登録済みかつレポートで有効な表示を、表示順に並べたもの。 */
export function resolveChartSelection(
  modes: readonly Mode[],
  requested?: string,
  fallback?: string,
): string | undefined {
  const available = modes.filter((mode) => !mode.isDisabled);
  return (
    available.find((mode) => mode.id === requested)?.id ??
    available.find((mode) => mode.id === fallback)?.id ??
    available[0]?.id
  );
}
