import { ScatterChart as _ScatterChart } from "@/components/charts/ScatterChart";
import { TreemapChart as _TreemapChart } from "@/components/charts/TreemapChart";
import { Tooltip } from "@/components/ui/tooltip";
import type { Result } from "@/type";
import { Box, Button, HStack, Icon } from "@chakra-ui/react";
import { Minimize2 } from "lucide-react";
import React, {
  useCallback, useEffect,
  useMemo, useReducer,
  useRef
} from "react";

const TRANSFORM_REGEX = /translate\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)/;
const NUMBER_REGEX = /^-?\d+(\.\d+)?$/;

const ScatterChart = React.memo(_ScatterChart);
const TreemapChart = React.memo(_TreemapChart);

type ReportProps = {
  result: Result;
  selectedChart: string;
  isFullscreen: boolean;
  onExitFullscreen: () => void;
  showClusterLabels: boolean;
  onToggleClusterLabels: (show: boolean) => void;
  treemapLevel: string;
  onTreeZoom: (level: string) => void;
};

type FilterState = {
  attributeFilters: Record<string, string[]>;
  numericRanges: Record<string, [number, number]>;
  enabledRanges: Record<string, boolean>;
  includeEmptyValues: Record<string, boolean>;
  textSearch: string;
};

type OverlayState = { opacity: number; isBlocking: boolean };
function overlayReducer(state: OverlayState, action: { type: "enter" | "leave" }) {
  switch (action.type) {
    case "enter": return { opacity: 0, isBlocking: false };
    case "leave": return { opacity: 0.3, isBlocking: true };
    default: return state;
  }
}

export const Chart = React.memo(function Chart({
  result, selectedChart, isFullscreen,
  onExitFullscreen, showClusterLabels,
  onToggleClusterLabels, treemapLevel,
  onTreeZoom, filterState,
}: ReportProps & { filterState?: FilterState }) {

  const { clusters = [], arguments: args = [], config } = result;

  const containerRef = useRef<HTMLDivElement>(null);
  const hoverbtn = useRef<HTMLElement | null>(null);
  const fadeTimeout = useRef<NodeJS.Timeout | null>(null);

  const [overlayState, dispatch] = useReducer(overlayReducer, { opacity: 0.3, isBlocking: true });

  useEffect(() => {
    hoverbtn.current = document.getElementById("fullScreenButtons");
    return () => { fadeTimeout.current && clearTimeout(fadeTimeout.current); };
  }, []);

  const handleMouseEnter = useCallback(() => {
    if (fadeTimeout.current) clearTimeout(fadeTimeout.current);
    dispatch({ type: "enter" });
  }, []);

  const handleMouseLeave = useCallback((e: React.MouseEvent) => {
    const r = containerRef.current?.getBoundingClientRect();
    if (!r) return;
    if (
      e.clientX < r.left || e.clientX > r.right ||
      e.clientY < r.top || e.clientY > r.bottom
    ) {
      fadeTimeout.current && clearTimeout(fadeTimeout.current);
      dispatch({ type: "leave" });
    }
  }, []);

  useEffect(() => {
    const handler = (e: WheelEvent) => {
      overlayState.isBlocking && e.preventDefault();
    };
    const el = containerRef.current;
    el && el.addEventListener("wheel", handler, { passive: false });
    return () => { el && el.removeEventListener("wheel", handler); };
  }, [overlayState.isBlocking]);

  const lowerSearch = useMemo(() => filterState?.textSearch.trim().toLowerCase() || "", [filterState?.textSearch]);

  const preprocessArgs = useMemo(() => {
    return args.map(a => {
      const argLC = a.argument.toLowerCase();
      const numAttrs = Object.fromEntries(Object.entries(a.attributes || {}).map(([k, v]) => [k, NUMBER_REGEX.test(String(v)) ? Number(v) : NaN]));
      return { arg_id: a.arg_id, argument: argLC, numeric: numAttrs, attributes: a.attributes };
    });
  }, [args]);

  const filteredArgumentIds = useMemo<string[] | undefined>(() => {
    if (!filterState) return undefined;
    const { attributeFilters, numericRanges, enabledRanges } = filterState;
    const hasText = lowerSearch !== "";
    const hasAttr = Object.values(attributeFilters).some(arr => arr.length > 0);
    const hasNum = Object.values(enabledRanges).some(Boolean);
    if (!hasText && !hasAttr && !hasNum) return undefined;
    return preprocessArgs
      .filter(a => {
        if (hasText && !a.argument.includes(lowerSearch)) return false;
        if (a.attributes) {
          for (const [k, vals] of Object.entries(attributeFilters)) {
            if (vals.length && !vals.includes(String(a.attributes[k] ?? ""))) return false;
          }
          for (const [k, range] of Object.entries(numericRanges)) {
            if (!enabledRanges[k]) continue;
            const v = a.numeric[k];
            if (isNaN(v) || v < range[0] || v > range[1]) return false;
          }
        }
        return true;
      })
      .map(a => a.arg_id);
  }, [preprocessArgs, filterState, lowerSearch]);

  const maxLevel = useMemo(() => clusters.length ? Math.max(...clusters.map(c => c.level ?? 0)) : 1, [clusters]);
  const targetLevel = selectedChart === "scatterAll" ? 1 : maxLevel;

  const commonProps = useMemo(() => ({
    clusterList: clusters,
    argumentList: args,
    filteredArgumentIds,
    showClusterLabels,
    config,
  }), [clusters, args, filteredArgumentIds, showClusterLabels, config]);

  const avoidHover = useCallback(() => {
    const hlayer = document.querySelector(".hoverlayer");
    const btn = hoverbtn.current;
    if (!hlayer || !btn) return;
    const hr = hlayer.getBoundingClientRect(), br = btn.getBoundingClientRect();
    if (br.bottom >= hr.top && br.top <= hr.bottom && br.right >= hr.left && br.left <= hr.right) {
      const d = br.bottom - hr.top;
      const t = hlayer.querySelector(".hovertext");
      t && t.setAttribute("transform", (t.getAttribute("transform") || "").replace(TRANSFORM_REGEX, (_, x, y) => `(${x},${parseFloat(y) + d})`));
      const p = hlayer.querySelector("path");
      p && p.setAttribute("d", (p.getAttribute("d") || "").replace(/M([^,]+),([^ ]+)/, (_, x, y) => `M${x},${parseFloat(y) - d}`));
    }
  }, []);

  if (isFullscreen) {
    return (
      <Box w="100%" h="100vh" pos="fixed" top={0} left={0} bgColor="#fff" zIndex={1000}>
        <HStack id="fullScreenButtons" pos="fixed" top={5} right={5} zIndex={101}>
          <Tooltip content="全画面終了" openDelay={0} closeDelay={0}>
            <Button onClick={onExitFullscreen} h="50px" borderWidth={2}>
              <Icon as={Minimize2} />
            </Button>
          </Tooltip>
        </HStack>
        {selectedChart === "treemap" ? (
          <TreemapChart {...commonProps} level={treemapLevel} onTreeZoom={onTreeZoom} onHover={avoidHover} />
        ) : (
          <ScatterChart {...commonProps} targetLevel={targetLevel} onHover={avoidHover} />
        )}
      </Box>
    );
  }

  return (
    <Box mx="auto" w="100%" maxW="1200px" mb={10} border="1px solid #ccc">
      <Box ref={containerRef} h="500px" pos="relative" onMouseEnter={handleMouseEnter} onMouseLeave={handleMouseLeave}>
        <Box pointerEvents={overlayState.isBlocking ? "none" : "auto"} h="100%" w="100%">
          {selectedChart === "treemap" ? (
            <TreemapChart {...commonProps} level={treemapLevel} onTreeZoom={onTreeZoom} />
          ) : (
            <ScatterChart {...commonProps} targetLevel={targetLevel} />
          )}
        </Box>
        <Box pos="absolute" top={0} left={0} right={0} bottom={0}
          bg="#CFD8DC" opacity={overlayState.opacity}
          transition="opacity 500ms ease" zIndex={10}
          pointerEvents={overlayState.isBlocking ? "auto" : "none"}
          onTouchMove={e => overlayState.isBlocking && e.preventDefault()}
        />
      </Box>
    </Box>
  );
});