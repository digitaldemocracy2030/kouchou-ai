"use client";

import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Argument, Comments } from "@/type";
import { Box, Text } from "@chakra-ui/react";
import { useState } from "react";

type SourceReference = Partial<Pick<Argument, "comment_id" | "comment_ids">>;

function sourceIds(opinion: SourceReference): string[] {
  // v2 の複数出典を優先し、旧レポートは単一の出典 ID に戻る。
  if (opinion.comment_ids !== undefined) {
    return Array.isArray(opinion.comment_ids)
      ? opinion.comment_ids.filter((id) => typeof id === "string" && id.length > 0)
      : [];
  }
  const id = opinion.comment_id;
  if (typeof id === "string") return id ? [id] : [];
  return typeof id === "number" && Number.isSafeInteger(id) ? [String(id)] : [];
}

function collectOriginalComments(opinions: readonly SourceReference[], comments?: Comments) {
  const seen = new Set<string>();
  const sources: { id: string; body: string }[] = [];
  let hasMissing = false;
  for (const opinion of opinions) {
    const ids = sourceIds(opinion);
    if (ids.length === 0) hasMissing = true;
    for (const id of ids) {
      if (seen.has(id)) continue;
      seen.add(id);
      const body = comments && Object.hasOwn(comments, id) ? comments[id]?.comment : undefined;
      if (typeof body === "string" && body.trim().length > 0) sources.push({ id, body });
      else hasMissing = true;
    }
  }
  return { sources, hasMissing };
}

function OriginalCommentDisclosure({ label, body, name }: { label: string; body: string; name?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details name={name} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <Box as="summary" color="blue.700" fontSize="sm" cursor="pointer" py={1}>
        {label}
      </Box>
      {open && (
        <Text fontSize="sm" whiteSpace="pre-wrap" overflowWrap="anywhere" color="gray.700" pl={4} pb={2}>
          {body}
        </Text>
      )}
    </details>
  );
}

export function OriginalComments({
  opinions,
  enabled,
  comments,
  disclosureGroup,
}: {
  opinions: readonly SourceReference[];
  enabled?: boolean;
  comments?: Comments;
  /** 同じ階層リスト内では、同じ原文が別の末端でも同時に開かないようにする。 */
  disclosureGroup?: string;
}) {
  const messages = useMessages();
  if (opinions.length === 0) return null;
  if (enabled !== true) {
    return (
      <Text mt={3} fontSize="sm" color="gray.600">
        {messages.originalCommentsNotPublic}
      </Text>
    );
  }

  const { sources, hasMissing } = collectOriginalComments(opinions, comments);
  if (sources.length === 0) {
    return (
      <Text mt={3} fontSize="sm" color="gray.600">
        {messages.originalCommentsMissing}
      </Text>
    );
  }

  return (
    <Box as="section" aria-label={messages.originalCommentCount(sources.length)} mt={3}>
      <Text fontSize="sm" color="gray.700" fontWeight="semibold">
        {messages.originalCommentCount(sources.length)}
      </Text>
      <Box as="ul" listStyleType="none" pl={0} m={0}>
        {sources.map(({ id, body }, index) => (
          <li key={id}>
            <OriginalCommentDisclosure
              label={messages.numberedOriginalComment(index + 1)}
              body={body}
              name={disclosureGroup ? `${disclosureGroup}-${id}` : undefined}
            />
          </li>
        ))}
      </Box>
      {hasMissing && (
        <Text fontSize="sm" color="gray.600" mt={1}>
          {messages.someOriginalCommentsMissing}
        </Text>
      )}
    </Box>
  );
}
