/**
 * HierarchyListChart
 *
 * Displays clusters as an expandable hierarchical list using ul/li elements:
 * the detail mode for reading everything. At the deepest level each opinion links
 * to its source when the report enables source links (same rule as the scatter plot).
 * Based on policy-pr-hub's HierarchicalBulletList component.
 */

"use client";

import { OriginalComments } from "@/components/report/OriginalComments";
import { Button } from "@/components/ui/button";
import { groupArgumentsByCluster, splitArgumentsByFilter, toIdSet } from "@/lib/argumentIndex";
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Argument, Cluster, Comments, Config } from "@/type";
import { Box, HStack, Icon, Link, Text, VStack } from "@chakra-ui/react";
import { ChevronRight, ExternalLink } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useId, useMemo, useRef, useState } from "react";

interface HierarchyListChartProps {
  clusterList: Cluster[];
  argumentList: Argument[];
  filteredArgumentIds?: string[];
  /** テキスト検索の文字列（空・undefined = 検索なし）。検索中は一致した意見を含むグループを開く（#1205） */
  textSearch?: string;
  onHover?: () => void;
  /** レポート設定。enable_source_link のときだけ最下層の意見に出典リンクを出す */
  config?: Config;
  // 元コメント本文（出典 ID → 本文）。
  comments?: Comments;
  oppositionClusterIds?: ReadonlySet<string>;
  onOpenOpposition?: (clusterId: string) => void;
  reopenClusterId?: string;
  /** 最初からこのグループと祖先を開き、最下層の意見まで見せてスクロールする（散布図の「このグループの意見をリストで見る」、#1207） */
  openClusterId?: string;
}

interface ClusterNode {
  id: string;
  level: number;
  parent: string;
  label: string;
  takeaway: string;
  value: number;
  children: ClusterNode[];
  isExpanded: boolean;
  isChildrenExpanded: boolean;
  arguments: Argument[];
}

function collectExpansion(
  nodes: ClusterNode[],
  expansion = new Map<string, Pick<ClusterNode, "isExpanded" | "isChildrenExpanded">>(),
) {
  for (const node of nodes) {
    if (node.isExpanded || node.isChildrenExpanded) {
      expansion.set(node.id, { isExpanded: node.isExpanded, isChildrenExpanded: node.isChildrenExpanded });
    }
    collectExpansion(node.children, expansion);
  }
  return expansion;
}

// すべてのグループについて、要約・子グループ・最下層の個別データをまとめて開く（open=false なら閉じる）
function setAllExpansion(nodes: ClusterNode[], open: boolean): ClusterNode[] {
  return nodes.map((node) => ({
    ...node,
    isExpanded: open,
    isChildrenExpanded: open,
    children: setAllExpansion(node.children, open),
  }));
}

// 指定したグループの要約・子グループ・最下層の意見までを開く。ほかのグループの開閉はそのまま
function expandSubtree(nodes: ClusterNode[], clusterId: string): ClusterNode[] {
  return nodes.map((node) =>
    node.id === clusterId
      ? setAllExpansion([node], true)[0]
      : { ...node, children: expandSubtree(node.children, clusterId) },
  );
}

// 一致した意見を含むグループを、最下層の個別データまで開く。一致しないグループの開閉はそのまま
function expandMatches(
  nodes: ClusterNode[],
  argumentsByCluster: ReadonlyMap<string, Argument[]>,
  filteredIdSet: ReadonlySet<string>,
): ClusterNode[] {
  return nodes.map((node) => {
    const hasMatch = (argumentsByCluster.get(node.id) ?? []).some((arg) => filteredIdSet.has(arg.arg_id));
    if (!hasMatch) return node;
    return {
      ...node,
      isExpanded: true,
      isChildrenExpanded: true,
      children: expandMatches(node.children, argumentsByCluster, filteredIdSet),
    };
  });
}

function ArgumentsDisplay({
  arguments: argumentsList,
  filteredIdSet,
  maxDisplay = 10,
  comments,
  showOriginalComments,
  disclosureGroup,
  showSourceLinks = false,
}: {
  arguments: Argument[];
  // フィルタ済み意見 ID の Set（undefined = フィルタなし）。配列の includes による線形探索を避けるため Set で受け取る
  filteredIdSet?: ReadonlySet<string>;
  maxDisplay?: number;
  comments?: Comments;
  showOriginalComments?: boolean;
  disclosureGroup: string;
  // 出典リンクを出すか（レポート設定 enable_source_link）。URL の無い意見には出さない
  showSourceLinks?: boolean;
}) {
  const messages = useMessages();
  const [showAll, setShowAll] = useState(false);
  // フィルタ中は一致した意見を先に並べる。最初の maxDisplay 件に入らず「さらに表示」の奥に隠れるのを防ぐ
  const orderedArguments = useMemo(() => {
    if (!filteredIdSet) return argumentsList;
    const { matching, notMatching } = splitArgumentsByFilter(argumentsList, filteredIdSet);
    return [...matching, ...notMatching];
  }, [argumentsList, filteredIdSet]);
  const displayArguments = showAll ? orderedArguments : orderedArguments.slice(0, maxDisplay);

  if (argumentsList.length === 0) {
    return (
      <Text fontSize="sm" color="gray.500">
        {messages.noItems}
      </Text>
    );
  }

  return (
    <Box mt={2}>
      <Text fontSize="sm" fontWeight="medium" color="gray.600" mb={2}>
        {messages.itemsHeading(argumentsList.length)}
      </Text>
      <Box as="ul" pl={4} m={0} listStyleType="disc">
        {displayArguments.map((arg) => {
          const isFiltered = filteredIdSet && !filteredIdSet.has(arg.arg_id);
          return (
            <Box as="li" key={arg.arg_id} mb={2} opacity={isFiltered ? 0.4 : 1}>
              <Text fontSize="sm" color="gray.700">
                {arg.argument}
              </Text>
              {showSourceLinks && arg.url && (
                <Link
                  href={arg.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  fontSize="xs"
                  color="blue.500"
                  _hover={{ color: "blue.600" }}
                  display="inline-flex"
                  alignItems="center"
                  gap={1}
                >
                  <Icon as={ExternalLink} w={3} h={3} />
                  {messages.sourceLink}
                </Link>
              )}
            </Box>
          );
        })}
      </Box>
      {argumentsList.length > maxDisplay && (
        <Box
          as="button"
          onClick={() => setShowAll(!showAll)}
          fontSize="xs"
          color="blue.500"
          _hover={{ color: "blue.600" }}
          textDecoration="underline"
          cursor="pointer"
          bg="transparent"
          border="none"
          p={0}
        >
          {showAll ? messages.showLess : messages.showMore(argumentsList.length - maxDisplay)}
        </Box>
      )}
      <OriginalComments
        opinions={filteredIdSet ? displayArguments.filter((arg) => filteredIdSet.has(arg.arg_id)) : displayArguments}
        enabled={showOriginalComments}
        comments={comments}
        disclosureGroup={disclosureGroup}
      />
    </Box>
  );
}

export function HierarchyListChart({
  clusterList,
  argumentList,
  filteredArgumentIds,
  textSearch,
  onHover,
  config,
  comments,
  oppositionClusterIds,
  onOpenOpposition,
  reopenClusterId,
  openClusterId,
}: HierarchyListChartProps) {
  const messages = useMessages();
  const disclosureGroup = useId();
  // 出典リンクは散布図と同じ条件（レポート設定で有効なときだけ）
  const showSourceLinks = Boolean(config?.enable_source_link);
  const [treeData, setTreeData] = useState<ClusterNode[]>([]);
  const restoredAction = useRef<HTMLButtonElement>(null);
  const scrollRestored = useRef(false);
  const openedLabel = useRef<HTMLParagraphElement>(null);
  const openedScrolled = useRef(false);
  // ツリーを作り直すときに、直前の展開状態をクラスタ ID で引き継ぐための参照（下の effect より先に更新する）
  const treeDataRef = useRef(treeData);
  useEffect(() => {
    treeDataRef.current = treeData;
  }, [treeData]);

  // cluster_id → 意見の索引。クラスタごとに全意見を filter すると、クラスタ数 × 意見数の走査になるため 1 回だけ作る
  const argumentsByCluster = useMemo(() => groupArgumentsByCluster(argumentList), [argumentList]);
  const filteredIdSet = useMemo(() => toIdSet(filteredArgumentIds), [filteredArgumentIds]);

  // Build tree structure from flat cluster list
  useEffect(() => {
    const clusterMap = new Map<string, ClusterNode>();
    // フィルタの適用・変更・解除のたびに clusterList は新しい配列になる。作り直しても開いていたクラスタは閉じない
    const previousExpansion = collectExpansion(treeDataRef.current);
    const isFirstBuild = treeDataRef.current.length === 0;
    const pathTarget = reopenClusterId ?? openClusterId;
    const reopenPath = new Set<string>();
    if (pathTarget && isFirstBuild) {
      const parentById = new Map(clusterList.map((cluster) => [cluster.id, cluster.parent]));
      let id: string | undefined = pathTarget;
      while (id && parentById.has(id) && !reopenPath.has(id)) {
        reopenPath.add(id);
        id = parentById.get(id);
      }
    }

    // Create nodes for all clusters
    const maxLevel = Math.max(...clusterList.map((c) => c.level));
    for (const cluster of clusterList) {
      // Find arguments belonging to this cluster (at deepest level)
      const clusterArguments = cluster.level === maxLevel ? (argumentsByCluster.get(cluster.id) ?? []) : [];

      clusterMap.set(cluster.id, {
        ...cluster,
        children: [],
        isExpanded: previousExpansion.get(cluster.id)?.isExpanded ?? reopenPath.has(cluster.id),
        isChildrenExpanded:
          previousExpansion.get(cluster.id)?.isChildrenExpanded ??
          (reopenPath.has(cluster.id) && cluster.id !== reopenClusterId),
        arguments: clusterArguments,
      });
    }

    // Build parent-child relationships
    const rootNodes: ClusterNode[] = [];
    for (const cluster of clusterList) {
      const node = clusterMap.get(cluster.id);
      if (!node) continue;

      if (!cluster.parent || cluster.parent === "") {
        rootNodes.push(node);
      } else {
        const parent = clusterMap.get(cluster.parent);
        if (parent) {
          parent.children.push(node);
        }
      }
    }

    // Sort children by value (descending)
    const sortChildren = (nodes: ClusterNode[]): ClusterNode[] => {
      return nodes
        .map((node) => ({
          ...node,
          children: sortChildren(node.children),
        }))
        .sort((a, b) => b.value - a.value);
    };

    const tree = sortChildren(rootNodes);
    setTreeData(openClusterId && isFirstBuild ? expandSubtree(tree, openClusterId) : tree);
  }, [clusterList, argumentsByCluster, reopenClusterId, openClusterId]);

  useEffect(() => {
    if (!treeData.length || !restoredAction.current || scrollRestored.current) return;
    scrollRestored.current = true;
    restoredAction.current.focus({ preventScroll: true });
    restoredAction.current.scrollIntoView?.({ block: "center" });
  }, [treeData]);

  // 散布図から移ってきたときは、開いたグループの見出しへスクロールし、フォーカスも移す（押したボタンは消えるため）
  useEffect(() => {
    if (!treeData.length || !openedLabel.current || openedScrolled.current) return;
    openedScrolled.current = true;
    openedLabel.current.focus({ preventScroll: true });
    openedLabel.current.scrollIntoView?.({ block: "start" });
  }, [treeData]);

  // テキスト検索中は、一致した意見を含むグループを開いて、意見まで辿れるようにする（#1205）。
  // 上の effect がツリーを作り直した後に適用されるよう、関数形式で直前の状態に重ねる。
  // 属性フィルタだけのときは開かない（一致が多く、全体が開いてしまうため）
  const isSearching = Boolean(textSearch?.trim());
  useEffect(() => {
    if (!isSearching || !filteredIdSet) return;
    setTreeData((prev) => expandMatches(prev, argumentsByCluster, filteredIdSet));
  }, [isSearching, filteredIdSet, argumentsByCluster]);

  const closeAllDescendants = (nodes: ClusterNode[]): ClusterNode[] => {
    return nodes.map((node) => ({
      ...node,
      isExpanded: false,
      isChildrenExpanded: false,
      children: closeAllDescendants(node.children),
    }));
  };

  const toggleExpanded = (nodeId: string) => {
    const updateNode = (nodes: ClusterNode[]): ClusterNode[] => {
      return nodes.map((node) => {
        if (node.id === nodeId) {
          const newIsExpanded = !node.isExpanded;
          return {
            ...node,
            isExpanded: newIsExpanded,
            isChildrenExpanded: newIsExpanded ? node.isChildrenExpanded : false,
            children: newIsExpanded ? node.children : closeAllDescendants(node.children),
          };
        }
        return { ...node, children: updateNode(node.children) };
      });
    };

    setTreeData(updateNode(treeData));
  };

  const toggleChildrenExpanded = (nodeId: string) => {
    const updateNode = (nodes: ClusterNode[]): ClusterNode[] => {
      return nodes.map((node) => {
        if (node.id === nodeId) {
          return { ...node, isChildrenExpanded: !node.isChildrenExpanded };
        }
        return { ...node, children: updateNode(node.children) };
      });
    };

    setTreeData(updateNode(treeData));
  };

  const expandAll = () => setTreeData(setAllExpansion(treeData, true));
  const collapseAll = () => setTreeData(setAllExpansion(treeData, false));

  // フィルタ中の各クラスタの件数（undefined = フィルタなし）。ClientContainer の clusterCounts・TreemapChart と同じく、
  // 一致した意見の cluster_ids すべてに 1 を足す。ツリーを作り直さないよう、表示時に Map を引くだけにする
  const filteredCounts = useMemo(() => {
    if (!filteredArgumentIds) return undefined;
    const allowed = new Set(filteredArgumentIds);
    const counts = new Map<string, number>();
    for (const arg of argumentList) {
      if (!allowed.has(arg.arg_id)) continue;
      for (const id of arg.cluster_ids) counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return counts;
  }, [argumentList, filteredArgumentIds]);

  // Calculate filtered state for each cluster
  const clusterFilterState = useMemo(() => {
    if (!filteredIdSet) return new Map<string, boolean>();

    const state = new Map<string, boolean>();

    for (const cluster of clusterList) {
      const clusterArgs = argumentsByCluster.get(cluster.id) ?? [];
      const hasMatchingArgs = clusterArgs.some((arg) => filteredIdSet.has(arg.arg_id));
      state.set(cluster.id, hasMatchingArgs);
    }

    return state;
  }, [clusterList, argumentsByCluster, filteredIdSet]);

  const renderClusterNode = (node: ClusterNode, depth = 0): ReactNode => {
    const hasChildren = node.children.length > 0;
    const hasArguments = node.arguments.length > 0;
    const hasOpposition = onOpenOpposition && oppositionClusterIds?.has(node.id);
    const hasExpandableContent = hasChildren || node.takeaway || hasArguments || hasOpposition;

    // Check if this cluster has any matching arguments (when filter is active)
    const isFiltered = filteredArgumentIds ? !clusterFilterState.get(node.id) : false;

    return (
      <Box key={node.id} mb={3} pl={depth > 0 ? `${depth * 24}px` : 0} onMouseEnter={onHover}>
        <Box display="flex" alignItems="flex-start" gap={2}>
          {hasExpandableContent ? (
            <Box
              as="button"
              onClick={() => toggleExpanded(node.id)}
              flexShrink={0}
              w={6}
              h={6}
              display="flex"
              alignItems="center"
              justifyContent="center"
              color="blue.500"
              _hover={{ color: "blue.600" }}
              cursor="pointer"
              bg="transparent"
              border="none"
              p={0}
              aria-label={node.isExpanded ? messages.collapse : messages.expand}
              aria-expanded={node.isExpanded}
            >
              <Icon
                as={ChevronRight}
                w={4}
                h={4}
                transform={node.isExpanded ? "rotate(90deg)" : "rotate(0deg)"}
                transition="transform 0.2s"
              />
            </Box>
          ) : (
            <Box w={6} h={6} display="flex" alignItems="center" justifyContent="center">
              <Box w={2} h={2} bg="gray.300" borderRadius="full" />
            </Box>
          )}

          <Box flex={1} opacity={isFiltered ? 0.4 : 1}>
            <Text
              ref={node.id === openClusterId ? openedLabel : undefined}
              tabIndex={node.id === openClusterId ? -1 : undefined}
              fontWeight="semibold"
              color="gray.800"
              mb={1}
            >
              {node.label}
              <Text as="span" fontWeight="normal" fontSize="sm" color="gray.500" ml={2}>
                {filteredCounts
                  ? `(${messages.filteredOfTotalCount(filteredCounts.get(node.id) ?? 0, node.value)})`
                  : `(${messages.opinionCount(node.value)})`}
              </Text>
              {hasOpposition && !node.isExpanded && (
                <Text as="span" fontSize="xs" color="blue.700" fontWeight="normal" ml={2}>
                  {messages.oppositionAvailable}
                </Text>
              )}
            </Text>

            {node.isExpanded && (
              <Box mb={2}>
                {node.takeaway && (
                  <Text fontSize="sm" color="gray.600" lineHeight="1.6" mb={2}>
                    {node.takeaway}
                  </Text>
                )}

                {hasOpposition && (
                  <Button
                    ref={node.id === reopenClusterId ? restoredAction : undefined}
                    size="xs"
                    variant="secondary"
                    onClick={() => onOpenOpposition?.(node.id)}
                  >
                    {messages.oppositionOpen}
                  </Button>
                )}

                {hasChildren && (
                  <Box mt={2}>
                    <Box
                      as="button"
                      onClick={() => toggleChildrenExpanded(node.id)}
                      fontSize="xs"
                      color="blue.500"
                      _hover={{ color: "blue.600" }}
                      textDecoration="underline"
                      cursor="pointer"
                      bg="transparent"
                      border="none"
                      p={0}
                    >
                      {node.isChildrenExpanded ? messages.closeChildren : messages.showChildren(node.children.length)}
                    </Box>
                  </Box>
                )}

                {hasArguments && !hasChildren && (
                  <Box mt={2}>
                    <Box
                      as="button"
                      onClick={() => toggleChildrenExpanded(node.id)}
                      fontSize="xs"
                      color="blue.500"
                      _hover={{ color: "blue.600" }}
                      textDecoration="underline"
                      cursor="pointer"
                      bg="transparent"
                      border="none"
                      p={0}
                    >
                      {node.isChildrenExpanded ? messages.closeItems : messages.showItems(node.arguments.length)}
                    </Box>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        </Box>

        {/* Render children */}
        {hasChildren && node.isChildrenExpanded && (
          <Box mt={2}>{node.children.map((child) => renderClusterNode(child, depth + 1))}</Box>
        )}

        {/* Render arguments */}
        {hasArguments && !hasChildren && node.isChildrenExpanded && (
          <Box mt={2} pl={`${(depth + 1) * 24}px`}>
            <ArgumentsDisplay
              arguments={node.arguments}
              filteredIdSet={filteredIdSet}
              comments={comments}
              showOriginalComments={config?.enable_original_comments}
              disclosureGroup={disclosureGroup}
              showSourceLinks={showSourceLinks}
            />
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Box h="100%" overflow="auto" p={4} bg="white">
      <VStack align="stretch" gap={0}>
        <Box mb={4}>
          <Text fontSize="xl" fontWeight="bold" color="gray.800" mb={1}>
            {messages.hierarchyList}
          </Text>
          <Text fontSize="sm" color="gray.600">
            {messages.hierarchyListDescription}
          </Text>
          <HStack gap={2} mt={3}>
            <Button variant="secondary" size="xs" onClick={expandAll}>
              {messages.expandAll}
            </Button>
            <Button variant="secondary" size="xs" onClick={collapseAll}>
              {messages.collapseAll}
            </Button>
          </HStack>
        </Box>

        <Box>{treeData.map((node) => renderClusterNode(node))}</Box>
      </VStack>
    </Box>
  );
}
