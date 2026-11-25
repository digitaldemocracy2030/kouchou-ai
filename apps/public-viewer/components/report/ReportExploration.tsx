"use client";

import { ChartCore } from "@/components/charts/ChartCore";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import type { Argument, Result } from "@/type";
import { Box, Button, Heading, Text } from "@chakra-ui/react";
import type { Data } from "plotly.js";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import {
  DEFAULT_EXPLORATION,
  type ExplorationSettings,
  MAX_GROUPS,
  categoryKeys,
  coordinateOpinions,
  explorationSettings,
  explorationUrl,
  exploreGroups,
  opinionStance,
  readExploration,
} from "./explorationGroups";

const palette = [
  "#006B68",
  "#A34319",
  "#2853A6",
  "#8C416F",
  "#536F2B",
  "#B65772",
  "#50519A",
  "#0080A1",
  "#88641B",
  "#554638",
  "#5F4074",
  "#266941",
];

const labels = {
  ja: {
    heading: "意見のグループを切り直す",
    unavailable: "散布図の座標がある意見が2件以上あるレポートで使えます。",
    groupCount: "グループ数",
    stance: "賛否の重み",
    topic: "話題",
    reason: "理由",
    weight: "の重み",
    none: "列を選ぶ",
    noStance: "このレポートに賛否スコアはありません。",
    noFields: "話題や理由として選べる文字列属性がありません。",
    help: "散布図の位置を保ち、重みに応じてグループの色分けを変えます。元レポートは更新されません。",
    actual: (count: number) => `区別できるグループは ${count} 個です。`,
    summary: (index: number, count: number) => `グループ ${index + 1}（${count.toLocaleString()} 件）`,
    distribution: (a: number, n: number, b: number, u: number) =>
      `賛成寄り ${a} ／ 賛否スコア 0 ${n} ／ 反対寄り ${b} ／ 不明 ${u}`,
    share: "この見方のリンクを作る",
    shareUrl: "共有リンク",
    noCoordinates: (count: number) => `座標がない意見 ${count.toLocaleString()} 件は対象外です。`,
  },
  en: {
    heading: "Regroup opinions",
    unavailable: "This view requires two or more opinions with scatterplot coordinates.",
    groupCount: "Number of groups",
    stance: "Stance weight",
    topic: "Topic",
    reason: "Reason",
    weight: " weight",
    none: "Select a field",
    noStance: "This report has no stance scores.",
    noFields: "No text attributes are available for topic or reason.",
    help: "Adjust the weights to recolor groups. Positions stay fixed and the original report stays as published.",
    actual: (count: number) => `There are ${count} distinguishable groups.`,
    summary: (index: number, count: number) => `Group ${index + 1} (${count.toLocaleString()} opinions)`,
    distribution: (a: number, n: number, b: number, u: number) =>
      `Leaning for ${a} / Score 0 ${n} / Leaning against ${b} / Unknown ${u}`,
    share: "Create a link to this view",
    shareUrl: "Share link",
    noCoordinates: (count: number) => `${count.toLocaleString()} opinions without coordinates were excluded.`,
  },
  ko: {
    heading: "의견 그룹 다시 나누기",
    unavailable: "산점도 좌표가 있는 의견이 2개 이상인 보고서에서 사용할 수 있습니다.",
    groupCount: "그룹 수",
    stance: "찬반 가중치",
    topic: "주제",
    reason: "이유",
    weight: " 가중치",
    none: "항목 선택",
    noStance: "이 보고서에는 찬반 점수가 없습니다.",
    noFields: "주제나 이유로 선택할 수 있는 텍스트 속성이 없습니다.",
    help: "가중치에 따라 그룹의 색이 바뀝니다. 좌표와 원본 보고서는 그대로 유지됩니다.",
    actual: (count: number) => `구분할 수 있는 그룹은 ${count}개입니다.`,
    summary: (index: number, count: number) => `그룹 ${index + 1} (${count.toLocaleString()}건)`,
    distribution: (a: number, n: number, b: number, u: number) =>
      `찬성 쪽 ${a} / 점수 0 ${n} / 반대 쪽 ${b} / 알 수 없음 ${u}`,
    share: "이 보기의 링크 만들기",
    shareUrl: "공유 링크",
    noCoordinates: (count: number) => `좌표가 없는 의견 ${count.toLocaleString()}건은 제외했습니다.`,
  },
};

type Labels = (typeof labels)[keyof typeof labels];

function Range({
  label,
  value,
  min = 0,
  max = 10,
  change,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  change: (value: number) => void;
}) {
  return (
    <label style={{ display: "grid", gap: "0.25rem" }}>
      <span>
        {label} {value}
      </span>
      <input
        aria-label={label}
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => change(event.target.valueAsNumber)}
      />
    </label>
  );
}

function stanceCounts(group: Argument[]) {
  let positive = 0;
  let zero = 0;
  let negative = 0;
  let unknown = 0;
  for (const opinion of group) {
    const score = opinionStance(opinion);
    if (score === undefined) unknown++;
    else if (score > 0) positive++;
    else if (score < 0) negative++;
    else zero++;
  }
  return [positive, zero, negative, unknown] as const;
}

function ExplorationBody({
  result,
  settings,
  onSettingsChange,
  copy,
}: {
  result: Result;
  settings: ExplorationSettings;
  onSettingsChange: (settings: ExplorationSettings) => void;
  copy: Labels;
}) {
  const [share, setShare] = useState("");
  const target = useRef<HTMLInputElement>(null);
  const opinions = useMemo(() => coordinateOpinions(result.arguments), [result.arguments]);
  const keys = useMemo(() => categoryKeys(opinions), [opinions]);
  const hasStance = useMemo(() => opinions.some((opinion) => opinionStance(opinion) !== undefined), [opinions]);
  const usable = useMemo(() => explorationSettings(settings, opinions, keys), [settings, opinions, keys]);
  const deferred = useDeferredValue(usable);
  const groups = useMemo(() => exploreGroups(opinions, deferred), [opinions, deferred]);
  const chartData = useMemo<Data[]>(
    () =>
      groups.map((group, index) => ({
        type: "scattergl",
        mode: "markers",
        x: group.map((opinion) => opinion.x),
        y: group.map((opinion) => opinion.y),
        name: copy.summary(index, group.length),
        hoverinfo: "name",
        marker: { color: palette[index], opacity: 0.8, size: 6 },
      })),
    [groups, copy],
  );

  function change(update: Partial<ExplorationSettings>) {
    onSettingsChange({ ...settings, ...update });
    setShare("");
  }

  useEffect(() => {
    if (share) target.current?.select();
  }, [share]);

  if (opinions.length < 2) return <Text>{copy.unavailable}</Text>;

  return (
    <Box mt="3" display="grid" gap="4">
      <Text>{copy.help}</Text>
      {opinions.length !== result.arguments.length && (
        <Text fontSize="sm">{copy.noCoordinates(result.arguments.length - opinions.length)}</Text>
      )}
      <Box display="grid" gap="4" gridTemplateColumns={{ base: "1fr", md: "repeat(2, minmax(0, 1fr))" }}>
        <Range
          label={copy.groupCount}
          value={usable.count}
          min={2}
          max={Math.min(MAX_GROUPS, opinions.length)}
          change={(count) => change({ count })}
        />
        {hasStance ? (
          <Range label={copy.stance} value={usable.stance} change={(stance) => change({ stance })} />
        ) : (
          <Text fontSize="sm">{copy.noStance}</Text>
        )}
        {keys.length ? (
          (["topic", "reason"] as const).map((kind) => {
            const field = `${kind}Key` as const;
            return (
              <Box key={kind} display="grid" gap="2">
                <label style={{ display: "grid", gap: "0.25rem" }}>
                  {copy[kind]}
                  <select
                    aria-label={copy[kind]}
                    value={usable[field]}
                    onChange={(event) =>
                      change({ [field]: event.target.value, [kind]: event.target.value ? settings[kind] || 5 : 0 })
                    }
                  >
                    <option value="">{copy.none}</option>
                    {keys.map((key) => (
                      <option key={key} value={key}>
                        {key}
                      </option>
                    ))}
                  </select>
                </label>
                {usable[field] && (
                  <Range
                    label={`${copy[kind]}${copy.weight}`}
                    value={usable[kind]}
                    change={(weight) => change({ [kind]: weight })}
                  />
                )}
              </Box>
            );
          })
        ) : (
          <Text fontSize="sm">{copy.noFields}</Text>
        )}
      </Box>
      {groups.length !== deferred.count && (
        <Text as="output" fontSize="sm">
          {copy.actual(groups.length)}
        </Text>
      )}
      <ChartCore
        data={chartData}
        layout={{
          height: 340,
          autosize: true,
          showlegend: false,
          margin: { l: 5, r: 5, t: 5, b: 5 },
          xaxis: { visible: false },
          yaxis: { visible: false },
        }}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%" }}
      />
      <Box display="grid" gap="2">
        {groups.map((group, index) => (
          <details key={group[0].arg_id}>
            <summary>
              <span aria-hidden="true" style={{ color: palette[index] }}>
                ●{" "}
              </span>
              {copy.summary(index, group.length)}
            </summary>
            {hasStance && <Text fontSize="sm">{copy.distribution(...stanceCounts(group))}</Text>}
            <ul style={{ paddingInlineStart: "1.5rem" }}>
              {group.slice(0, 3).map((opinion) => (
                <li key={opinion.arg_id}>{opinion.argument}</li>
              ))}
            </ul>
          </details>
        ))}
      </Box>
      <Button
        variant="outline"
        justifySelf="start"
        onClick={() => {
          const url = explorationUrl(window.location.href, usable).href;
          window.history.replaceState(window.history.state, "", url);
          setShare(url);
        }}
      >
        {copy.share}
      </Button>
      {share && (
        <input
          aria-label={copy.shareUrl}
          ref={target}
          readOnly
          value={share}
          onFocus={(event) => event.currentTarget.select()}
        />
      )}
    </Box>
  );
}

export function ReportExploration({ result }: { result: Result }) {
  const { language } = useLanguage();
  const copy = labels[language];
  const [settings, setSettings] = useState<ExplorationSettings>(DEFAULT_EXPLORATION);
  const [open, setOpen] = useState(false);
  const title = useRef<HTMLHeadingElement>(null);
  const scatterEnabled =
    !result.visualizationConfig?.enabledCharts ||
    result.visualizationConfig.enabledCharts.some((chart) =>
      ["scatterAll", "scatterDetail", "scatterDensity"].includes(chart),
    );

  useEffect(() => {
    if (!scatterEnabled) return;
    const settings = readExploration(window.location.search);
    if (!settings) return;
    setSettings(settings);
    setOpen(true);
    if (window.location.hash === "#report-exploration") title.current?.focus();
  }, [scatterEnabled]);
  if (!scatterEnabled) return null;

  return (
    <Box as="section" id="report-exploration" maxW="750px" mx="auto" my="8" p="5" borderWidth="1px" borderRadius="lg">
      <Heading ref={title} tabIndex={-1} as="h2" size="md">
        <Button
          variant="ghost"
          aria-expanded={open}
          aria-controls="report-exploration-body"
          onClick={() => setOpen(!open)}
        >
          {copy.heading}
        </Button>
      </Heading>
      <div id="report-exploration-body">
        {open && <ExplorationBody result={result} settings={settings} onSettingsChange={setSettings} copy={copy} />}
      </div>
    </Box>
  );
}
