"use client";

import type { Cluster } from "@/type";
import { Box, Heading, Link, Text } from "@chakra-ui/react";
import { MessagesSquareIcon } from "lucide-react";
import { useEffect, useRef } from "react";

type Props = {
  cluster: Cluster;
  onNavigate?: () => void;
  /** 属性フィルター適用後の件数（未指定なら cluster.value を表示） */
  count?: number;
  /** フィルター適用中かどうか（表示ラベルの切り替えに使う） */
  isFiltering?: boolean;
  /** 散布図で選択中のクラスタかどうか（連動ハイライト用） */
  isSelected?: boolean;
};

export function ClusterOverview({ cluster, onNavigate, count, isFiltering, isSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  // 散布図でこのクラスタが選択されたら、連動して一覧の該当項目へスクロールする
  useEffect(() => {
    if (isSelected) {
      containerRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [isSelected]);

  // フィルター適用時はフィルター後の件数を優先し、未指定時は元の件数にフォールバックする
  const displayCount = count ?? cluster.value;

  return (
    <Box
      ref={containerRef}
      mx={"auto"}
      maxW={"750px"}
      mb={12}
      aria-current={isSelected ? "true" : undefined}
      borderLeftWidth={isSelected ? "4px" : "0"}
      borderLeftColor={isSelected ? "cyan.500" : "transparent"}
      pl={isSelected ? 4 : 0}
      transition={"border-color 0.2s ease, padding 0.2s ease"}
    >
      <Box mb={2}>
        <Link
          id={cluster.label}
          href={onNavigate ? "#report-chart" : `#${cluster.label}`}
          onClick={onNavigate}
          className={"headingColor"}
          position={"relative"}
          _hover={{
            "&:before": {
              content: '"#"',
              fontSize: "2xl",
              position: "absolute",
              left: "-1.4rem",
            },
          }}
        >
          <Heading fontSize={"2xl"} mb={0}>
            {cluster.label}
          </Heading>
        </Link>
        <Text fontWeight={"bold"} display={"flex"} gap={1} mt={2}>
          <MessagesSquareIcon size={20} />
          {displayCount.toLocaleString()}件{isFiltering ? "（フィルター後）" : ""}
        </Text>
      </Box>
      <Text>{cluster.takeaway}</Text>
    </Box>
  );
}
