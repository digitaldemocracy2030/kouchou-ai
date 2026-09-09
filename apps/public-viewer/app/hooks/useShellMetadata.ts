"use client";

import { useEffect } from "react";

/** The packager writes initial metadata; shell navigation updates the same tags.
 * Loading leaves packaged metadata intact, including unlisted noindex.
 * generateMetadata must not also own these tags in shell mode.
 */
export function useShellMetadata(title: string | undefined, noindex = false) {
  useEffect(() => {
    if (title === undefined) return;
    document.title = title;
    let robots = document.head.querySelector<HTMLMetaElement>('meta[name="robots"]');
    if (!robots) {
      robots = document.createElement("meta");
      robots.name = "robots";
      document.head.appendChild(robots);
    }
    robots.content = noindex ? "noindex, nofollow" : "index, follow";
  }, [title, noindex]);
}
