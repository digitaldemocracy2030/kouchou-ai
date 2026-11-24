"use client";

import { groupArgumentsByCluster, toIdSet } from "@/lib/argumentIndex";
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Argument, OppositionAxis, Result } from "@/type";
import { Box, Button, Heading, Link, NativeSelect, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { ArrowLeft } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

const PAGE_SIZE = 20;

type ScoredOpinion = { opinion: Argument; score: number };

function OpinionSide({
  title,
  opinions,
  side,
  sourceLinks,
}: {
  title: string;
  opinions: ScoredOpinion[];
  side: "left" | "right";
  sourceLinks: boolean;
}) {
  const messages = useMessages();
  const [limit, setLimit] = useState(PAGE_SIZE);
  const accent = side === "left" ? "blue.700" : "orange.800";

  return (
    <Box minW={0} p={{ base: 3, md: 4 }} borderRadius="md" bg={side === "left" ? "blue.50" : "orange.50"}>
      <Heading as="h4" size="sm" color={accent} overflowWrap="anywhere">
        {title}
      </Heading>
      <Text fontSize="sm" color="gray.700" mb={3}>
        {messages.opinionCount(opinions.length)}
      </Text>
      {opinions.length === 0 && <Text fontSize="sm">{messages.noItems}</Text>}
      <Stack as="ul" gap={2} listStyle="none" p={0} m={0}>
        {opinions.slice(0, limit).map(({ opinion, score }) => (
          <Box key={opinion.arg_id} as="li" display="flex" gap={2} p={3} borderRadius="md" bg="white">
            <Text
              as="span"
              flexShrink={0}
              color={accent}
              fontSize="sm"
              fontWeight="bold"
              title={messages.oppositionScore(score)}
            >
              {score}
            </Text>
            <Box minW={0}>
              <Text fontSize="sm" overflowWrap="anywhere">
                {opinion.argument}
              </Text>
              {sourceLinks && opinion.url && (
                <Link href={opinion.url} target="_blank" rel="noopener noreferrer" fontSize="sm" color="blue.700">
                  {messages.sourceLink}
                </Link>
              )}
            </Box>
          </Box>
        ))}
      </Stack>
      {opinions.length > limit && (
        <Button mt={3} size="sm" variant="outline" onClick={() => setLimit(limit + PAGE_SIZE)}>
          {messages.showMore(opinions.length - limit)}
        </Button>
      )}
    </Box>
  );
}

function DiscussionPoints({ title, points }: { title: string; points?: string[] }) {
  const visiblePoints = Array.isArray(points) ? points.filter((point) => typeof point === "string" && point) : [];
  if (visiblePoints.length === 0) return null;
  return (
    <Box as="details" fontSize="sm">
      <Box as="summary" cursor="pointer" fontWeight="semibold">
        {title}
      </Box>
      <Box as="ul" pl={5} mt={2} listStyleType="disc">
        {visiblePoints.map((point, index) => (
          <Box as="li" key={`${index}:${point}`} overflowWrap="anywhere">
            {point}
          </Box>
        ))}
      </Box>
    </Box>
  );
}

type Props = {
  result: Result;
  axes: OppositionAxis[];
  filteredArgumentIds?: string[];
  initialClusterId?: string;
  onBack?: () => void;
};

export function OppositionChart({ result, axes, filteredArgumentIds, initialClusterId, onBack }: Props) {
  const messages = useMessages();
  const sectionRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const clusterControl = useId();
  const axisControl = useId();
  const [clusterId, setClusterId] = useState(initialClusterId);
  const [axisId, setAxisId] = useState<string>();
  const clusterIds = new Set(axes.map((axis) => axis.cluster_id));
  const topics = result.clusters.filter((cluster) => clusterIds.has(cluster.id));
  const topic = topics.find((cluster) => cluster.id === clusterId) ?? topics[0];
  const topicAxes = axes.filter((axis) => axis.cluster_id === topic?.id);
  const axis = topicAxes.find((candidate) => candidate.id === axisId) ?? topicAxes[0];
  const argumentsByCluster = useMemo(() => groupArgumentsByCluster(result.arguments), [result.arguments]);
  const filteredIds = useMemo(() => toIdSet(filteredArgumentIds), [filteredArgumentIds]);

  useEffect(() => {
    if (onBack) {
      headingRef.current?.focus({ preventScroll: true });
      sectionRef.current?.scrollIntoView?.({ block: "start" });
    }
  }, [onBack]);

  if (!topic || !axis) return <Text p={4}>{messages.oppositionUnavailable}</Text>;

  const left: ScoredOpinion[] = [];
  const right: ScoredOpinion[] = [];
  let notApplicable = 0;
  let unscored = 0;
  for (const opinion of argumentsByCluster.get(topic.id) ?? []) {
    if (filteredIds && !filteredIds.has(opinion.arg_id)) continue;
    const score = Object.hasOwn(axis.scores, opinion.arg_id) ? axis.scores[opinion.arg_id] : undefined;
    if (score === null) {
      notApplicable++;
    } else if (typeof score === "number" && Number.isInteger(score) && score >= 1 && score <= 6) {
      const side = score <= 3 ? left : right;
      side.push({ opinion, score });
    } else {
      unscored++;
    }
  }
  left.sort((a, b) => a.score - b.score);
  right.sort((a, b) => b.score - a.score);
  const total = left.length + right.length + notApplicable + unscored;

  return (
    <Stack as="section" ref={sectionRef} gap={4} p={{ base: 4, md: 6 }} bg="white" color="gray.900">
      <Box>
        {onBack && (
          <Button size="sm" variant="ghost" onClick={onBack} mb={2}>
            <ArrowLeft aria-hidden />
            {messages.oppositionBack}
          </Button>
        )}
        <Heading as="h2" size="lg" ref={headingRef} tabIndex={-1}>
          {messages.oppositionHeading}
        </Heading>
      </Box>
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
        {initialClusterId ? (
          <Box minW={0}>
            <Text fontWeight="medium" mb={1}>
              {messages.oppositionTopic}
            </Text>
            <Text overflowWrap="anywhere">{topic.label}</Text>
          </Box>
        ) : (
          <Box minW={0}>
            <Text asChild display="block" fontWeight="medium" mb={1}>
              <label htmlFor={clusterControl}>{messages.oppositionTopic}</label>
            </Text>
            <NativeSelect.Root>
              <NativeSelect.Field
                id={clusterControl}
                value={topic.id}
                onChange={(event) => {
                  setClusterId(event.target.value);
                  setAxisId(undefined);
                }}
              >
                {topics.map((cluster) => (
                  <option key={cluster.id} value={cluster.id}>
                    {cluster.label}
                  </option>
                ))}
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>
          </Box>
        )}
        <Box minW={0}>
          <Text asChild display="block" fontWeight="medium" mb={1}>
            <label htmlFor={axisControl}>{messages.oppositionAxis}</label>
          </Text>
          <NativeSelect.Root>
            <NativeSelect.Field id={axisControl} value={axis.id} onChange={(event) => setAxisId(event.target.value)}>
              {topicAxes.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </option>
              ))}
            </NativeSelect.Field>
            <NativeSelect.Indicator />
          </NativeSelect.Root>
        </Box>
      </SimpleGrid>
      <Box>
        <Heading as="h3" size="md" overflowWrap="anywhere">
          {axis.name}
        </Heading>
        <Text fontSize="sm" color="gray.700" mt={1}>
          {messages.opinionCount(total)}
          {filteredIds && messages.filteredCountSuffix}
          {" · "}
          {messages.oppositionNotApplicable(notApplicable)}
          {unscored > 0 && ` · ${messages.oppositionUnscored(unscored)}`}
        </Text>
        <Text fontSize="sm" color="gray.600" mt={1}>
          {messages.oppositionReadingNote}
        </Text>
      </Box>
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} alignItems="start">
        <OpinionSide
          key={`${axis.id}:left`}
          title={axis.left_pole}
          opinions={left}
          side="left"
          sourceLinks={Boolean(result.config.enable_source_link)}
        />
        <OpinionSide
          key={`${axis.id}:right`}
          title={axis.right_pole}
          opinions={right}
          side="right"
          sourceLinks={Boolean(result.config.enable_source_link)}
        />
      </SimpleGrid>
      <DiscussionPoints title={messages.oppositionAgreements} points={axis.agreements} />
      <DiscussionPoints title={messages.oppositionConflicts} points={axis.conflicts} />
    </Stack>
  );
}
