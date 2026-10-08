import { useMessages } from "@/lib/i18n/LanguageContext";
import { treemapContext } from "./treemapContext";

type Props = {
  clusters: Parameters<typeof treemapContext>[0];
  arguments: Parameters<typeof treemapContext>[1];
  level: string;
  filteredIds?: Iterable<string> | null;
  onNavigate: (id: string) => void;
};

export function TreemapDetails({ clusters, arguments: opinions, level, filteredIds, onNavigate }: Props) {
  const messages = useMessages();
  const context = treemapContext(clusters, opinions, level, filteredIds);
  if (!context.current) return null;
  const denominatorLabel = context.filtering ? messages.allOpinionsAfterFilter : messages.allOpinions;
  const metrics = (item: typeof context.current) =>
    item && messages.metrics(item.count, denominatorLabel, item.percentage);
  return (
    <section aria-label={messages.treemapDetailsLabel} style={{ maxWidth: 750, margin: "24px auto", lineHeight: 1.8 }}>
      {context.parent && (
        <nav
          aria-label={messages.treemapNavLabel}
          style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}
        >
          <button
            type="button"
            onClick={() => context.parent && onNavigate(context.parent.id)}
            style={{ textDecoration: "underline" }}
          >
            {messages.goUp}
          </button>
          {context.root && context.parent.id !== context.root.id && (
            <button
              type="button"
              onClick={() => context.root && onNavigate(context.root.id)}
              style={{ textDecoration: "underline" }}
            >
              {messages.goRoot}
            </button>
          )}
        </nav>
      )}
      <h2 style={{ fontSize: "1.4rem", fontWeight: 700 }}>
        {messages.showing}: {context.current.label}
      </h2>
      <p>{metrics(context.current)}</p>
      <p>{context.current.takeaway}</p>
      {context.filtering && <p>{messages.filteredMetricsNote}</p>}
      {context.current.count === 0 && <p>{messages.noOpinionsHere}</p>}
      {context.children.length > 0 ? (
        <>
          <h3 style={{ fontWeight: 700, marginTop: 24 }}>{messages.groupsInLevel}</h3>
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
        !context.isOpinion && context.current.count > 0 && <p>{messages.leafHint}</p>
      )}
    </section>
  );
}
