import { Box, Field, HStack, Heading, NativeSelect, Text, VStack, chakra } from "@chakra-ui/react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { ParticipantVotes } from "../polisImport";
import { type ParticipantPoint, projectParticipants } from "../polisProjection";

const DAY = 86_400_000;
const groupColors = [
  "teal.600",
  "purple.600",
  "orange.600",
  "blue.600",
  "pink.600",
  "green.700",
  "cyan.700",
  "red.600",
];
const ungrouped = "gray.500";
const dateLabel = (timestamp: number) => new Date(timestamp).toISOString().slice(0, 10);

export function PolisParticipantPlot({ votes, comments }: { votes: ParticipantVotes; comments: { id: string }[] }) {
  const projection = useMemo(
    () =>
      projectParticipants(
        votes,
        comments.map((comment) => comment.id),
      ),
    [votes, comments],
  );
  const [day, setDay] = useState<number | null>(null);
  const [selectedVoter, setSelectedVoter] = useState("");
  const canvas = useRef<HTMLCanvasElement>(null);
  const markers = useRef<Array<{ x: number; y: number; point: ParticipantPoint }>>([]);
  const firstDay = projection.start === undefined ? undefined : Math.floor(projection.start / DAY);
  const lastDay = projection.end === undefined ? undefined : Math.floor(projection.end / DAY);
  const currentDay = day ?? lastDay;
  const timestamp = currentDay === undefined ? undefined : Math.min((currentDay + 1) * DAY - 1, projection.end ?? 0);
  const points = useMemo(() => projection.pointsAt(timestamp), [projection, timestamp]);
  const groups = useMemo(() => {
    const IDs = [...new Set(projection.final.flatMap((point) => (point.group === undefined ? [] : [point.group])))];
    IDs.sort((a, b) => Number(a) - Number(b));
    return new Map(IDs.map((group, index) => [group, groupColors[index % groupColors.length]]));
  }, [projection]);
  const selected = points.find((point) => point.voter === selectedVoter);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const context = element.getContext("2d");
    if (!context) return;

    const draw = () => {
      const { width, height } = element.getBoundingClientRect();
      if (!width || !height) return;
      const ratio = window.devicePixelRatio || 1;
      element.width = Math.round(width * ratio);
      element.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      const css = getComputedStyle(element);
      const color = (token: string, fallback: string) =>
        css.getPropertyValue(`--chakra-colors-${token.replace(".", "-")}`).trim() || fallback;
      const midpointX = width / 2;
      const midpointY = height / 2;
      const scale = (Math.min(width, height) / 2 - 18) / (projection.extent || 1);
      const plot = (x: number, y: number) => [midpointX + x * scale, midpointY - y * scale] as const;

      context.strokeStyle = color("gray.300", "#cbd5e0");
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(8, midpointY);
      context.lineTo(width - 8, midpointY);
      context.moveTo(midpointX, 8);
      context.lineTo(midpointX, height - 8);
      context.stroke();

      const trail = projection.trailFor(selectedVoter, timestamp);
      if (trail.length > 1) {
        context.strokeStyle = color(groups.get(selected?.group ?? "") ?? "blue.700", "#2b6cb0");
        context.lineWidth = 1.8;
        context.beginPath();
        context.moveTo(...plot(trail[0].x, trail[0].y));
        for (const point of trail.slice(1)) context.lineTo(...plot(point.x, point.y));
        context.stroke();
      }

      const palette = new Map([...groups].map(([group, token]) => [group, color(token, "#2b6cb0")]));
      const neutral = color(ungrouped, "#718096");
      markers.current = points.map((point) => {
        const [x, y] = plot(point.x, point.y);
        context.fillStyle = palette.get(point.group ?? "") ?? neutral;
        context.globalAlpha = selected && point !== selected ? 0.37 : 0.82;
        context.beginPath();
        context.arc(x, y, 3.2, 0, Math.PI * 2);
        context.fill();
        return { x, y, point };
      });
      context.globalAlpha = 1;
      if (selected) {
        const [x, y] = plot(selected.x, selected.y);
        context.strokeStyle = palette.get(selected.group ?? "") ?? neutral;
        context.lineWidth = 2;
        context.beginPath();
        context.arc(x, y, 7, 0, Math.PI * 2);
        context.stroke();
      }
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(element);
    return () => observer.disconnect();
  }, [groups, points, projection, selected, selectedVoter, timestamp]);

  if (projection.final.length === 0) return <Text>散布図に使える参加者の投票がありません。</Text>;

  return (
    <VStack align="stretch" gap={3} mt={5}>
      <Box>
        <Heading size="md">参加者の散布図</Heading>
        <Text fontSize="sm" color="fg.muted">
          1点は1人です。賛否・パスの組み合わせを2つの主成分に投影しています。
        </Text>
      </Box>
      {firstDay !== undefined && lastDay !== undefined && currentDay !== undefined && timestamp !== undefined && (
        <Field.Root>
          <Field.Label>投票日 {dateLabel(timestamp)} UTC</Field.Label>
          {firstDay !== lastDay && (
            <chakra.input
              type="range"
              aria-label="投票日"
              aria-valuetext={dateLabel(timestamp)}
              width="full"
              min={firstDay}
              max={lastDay}
              value={currentDay}
              onChange={(event) => setDay(event.currentTarget.valueAsNumber)}
            />
          )}
          <Field.HelperText>各日までの投票を、最終日の軸で表示しています。</Field.HelperText>
        </Field.Root>
      )}
      <HStack justify="space-between" flexWrap="wrap">
        <Text fontSize="sm">表示 {points.length} 人</Text>
        <Text fontSize="xs" color="fg.muted">
          横軸 第1主成分／縦軸 第2主成分
        </Text>
      </HStack>
      <chakra.canvas
        ref={canvas}
        role="img"
        aria-label={`賛否のパターンで配置した参加者の散布図、${points.length}人`}
        width="full"
        height={{ base: "260px", md: "330px" }}
        display="block"
        borderWidth="1px"
        borderRadius="md"
        onClick={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          let nearest: ParticipantPoint | undefined;
          let distance = 12;
          for (const marker of markers.current) {
            const candidate = Math.hypot(marker.x - (event.clientX - rect.left), marker.y - (event.clientY - rect.top));
            if (candidate < distance) {
              distance = candidate;
              nearest = marker.point;
            }
          }
          if (nearest) setSelectedVoter(nearest.voter);
        }}
      />
      {groups.size > 0 && (
        <Box>
          <Text fontSize="xs" color="fg.muted">
            エクスポート時点のPolisグループ
          </Text>
          <HStack flexWrap="wrap" gap={3}>
            {[...groups].map(([group, color]) => (
              <HStack gap={1} key={group}>
                <Box bg={color} borderRadius="full" w={2} h={2} aria-hidden="true" />
                <Text fontSize="sm">グループ {group}</Text>
              </HStack>
            ))}
            {projection.final.some((point) => point.group === undefined) && (
              <HStack gap={1}>
                <Box bg={ungrouped} borderRadius="full" w={2} h={2} aria-hidden="true" />
                <Text fontSize="sm">未分類</Text>
              </HStack>
            )}
          </HStack>
        </Box>
      )}
      <Field.Root>
        <Field.Label>参加者</Field.Label>
        <NativeSelect.Root>
          <NativeSelect.Field value={selectedVoter} onChange={(event) => setSelectedVoter(event.target.value)}>
            <option value="">参加者を選ぶ</option>
            {projection.final.map((point) => (
              <option key={point.voter} value={point.voter}>
                参加者 {point.voter}
              </option>
            ))}
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        {selected && (
          <Field.HelperText>
            賛成 {selected.agree}／反対 {selected.disagree}／パス {selected.pass}
          </Field.HelperText>
        )}
        {selectedVoter && !selected && <Field.HelperText>この日までの投票はありません。</Field.HelperText>}
      </Field.Root>
    </VStack>
  );
}
