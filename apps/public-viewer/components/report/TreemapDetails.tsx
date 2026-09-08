import { treemapContext } from "./treemapContext";

type Props = {
  clusters: Parameters<typeof treemapContext>[0];
  arguments: Parameters<typeof treemapContext>[1];
  level: string;
  filteredIds?: Iterable<string> | null;
  onNavigate: (id: string) => void;
};

export function TreemapDetails({ clusters, arguments: opinions, level, filteredIds, onNavigate }: Props) {
  const context = treemapContext(clusters, opinions, level, filteredIds);
  if (!context.current) return null;
  const denominatorLabel = context.filtering ? "フィルター後の全意見" : "全意見";
  const metrics = (item: typeof context.current) =>
    item && `${item.count.toLocaleString()}件（${denominatorLabel}に対する割合: ${item.percentage}）`;
  return (
    <section aria-label="階層図の説明" style={{ maxWidth: 750, margin: "24px auto", lineHeight: 1.8 }}>
      {context.parent && (
        <nav aria-label="階層の移動" style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
          <button
            type="button"
            onClick={() => context.parent && onNavigate(context.parent.id)}
            style={{ textDecoration: "underline" }}
          >
            一つ上に戻る
          </button>
          {context.root && context.parent.id !== context.root.id && (
            <button
              type="button"
              onClick={() => context.root && onNavigate(context.root.id)}
              style={{ textDecoration: "underline" }}
            >
              全体に戻る
            </button>
          )}
        </nav>
      )}
      <h2 style={{ fontSize: "1.4rem", fontWeight: 700 }}>表示中: {context.current.label}</h2>
      <p>{metrics(context.current)}</p>
      <p>{context.current.takeaway}</p>
      {context.filtering && (
        <p>件数と割合はフィルター後の値です。グループの説明はフィルター前の全意見を基に生成しています。</p>
      )}
      {context.current.count === 0 && <p>この階層に該当する意見はありません。</p>}
      {context.children.length > 0 ? (
        <>
          <h3 style={{ fontWeight: 700, marginTop: 24 }}>この階層の意見グループ</h3>
          {context.children.map((group) => (
            <article key={group.id} style={{ marginTop: 20 }}>
              <h4>
                <button
                  type="button"
                  onClick={() => onNavigate(group.id)}
                  style={{ textAlign: "left", textDecoration: "underline", fontWeight: 700 }}
                >
                  {group.label}
                </button>
              </h4>
              <p>{metrics(group)}</p>
              <p>{group.takeaway}</p>
            </article>
          ))}
        </>
      ) : (
        !context.isOpinion &&
        context.current.count > 0 && <p>図の各領域は個別の意見です。選択するとその意見を表示します。</p>
      )}
    </section>
  );
}
