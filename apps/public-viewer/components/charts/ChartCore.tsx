"use client";

import { LoadingBar } from "@/components/report/LoadingBar";
import jaLocale from "@/lib/plotly-locale-ja";
import dynamic from "next/dynamic";

export const ChartCore = dynamic(
  async () => {
    const Plotly = await import("plotly.js/lib/core");
    const Scatter = await import("plotly.js/lib/scatter");
    const Sunburst = await import("plotly.js/lib/sunburst");
    const Treemap = await import("plotly.js/lib/treemap");

    // ズームとパン機能のために必要なモジュール
    const ScatterGL = await import("plotly.js/lib/scattergl");

    const createPlotlyComponent = (await import("react-plotly.js/factory")).default;

    Plotly.register([Scatter, Sunburst, Treemap, ScatterGL]);
    Plotly.register(jaLocale);

    return createPlotlyComponent(Plotly);
  },
  {
    ssr: false,
    loading: () => <LoadingBar loaded={100} max={100} isVisualizing />,
  },
);
