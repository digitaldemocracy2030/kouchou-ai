"use client";

import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Result } from "@/type";
import { Box, Heading, List, Text } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";

export function ReportTopicLink({ result }: { result: Result }) {
  const messages = useMessages();
  const [topicId, setTopicId] = useState<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const topic = result.clusters.find((cluster) => cluster.level === 1 && cluster.id === topicId);

  useEffect(() => {
    setTopicId(new URLSearchParams(window.location.search).get("topic"));
  }, []);
  useEffect(() => {
    if (topic && window.location.hash === "#report-topic") heading.current?.focus();
  }, [topic]);
  if (!topic) return null;

  const examples: string[] = [];
  let count = 0;
  for (const opinion of result.arguments) {
    if (!opinion.cluster_ids.includes(topic.id)) continue;
    count++;
    if (examples.length < 3 && opinion.argument.trim() && !examples.includes(opinion.argument.trim())) {
      examples.push(opinion.argument.trim());
    }
  }

  return (
    <Box as="section" maxW="750px" mx="auto" my="8" p="5" borderWidth="1px" borderRadius="lg">
      <Heading id="report-topic" ref={heading} tabIndex={-1} size="lg">
        {topic.label}
      </Heading>
      <Text mt="2">{messages.opinionCount(count)}</Text>
      <Text mt="2">{topic.takeaway}</Text>
      {examples.length > 0 && (
        <List.Root mt="3" ps="5">
          {examples.map((text) => (
            <List.Item key={text}>{text}</List.Item>
          ))}
        </List.Root>
      )}
    </Box>
  );
}
