/**
 * HierarchyListChart
 *
 * Displays clusters as an expandable hierarchical list using ul/li elements.
 * Based on policy-pr-hub's HierarchicalBulletList component.
 */

"use client";

import type { Argument, Cluster } from "@/type";
import { Box, Icon, Text, VStack } from "@chakra-ui/react";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

interface HierarchyListChartProps {
  clusterList: Cluster[];
  argumentList: Argument[];
  filteredArgumentIds?: string[];
  onHover?: () => void;
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

function ArgumentsDisplay({
  arguments: argumentsList,
  filteredArgumentIds,
  maxDisplay = 10,
}: {
  arguments: Argument[];
  filteredArgumentIds?: string[];
  maxDisplay?: number;
}) {
  const [showAll, setShowAll] = useState(false);
  const displayArguments = showAll ? argumentsList : argumentsList.slice(0, maxDisplay);

  if (argumentsList.length === 0) {
    return (
      <Text fontSize="sm" color="gray.500">
        個別データがありません
      </Text>
    );
  }

  return (
    <Box mt={2}>
      <Text fontSize="sm" fontWeight="medium" color="gray.600" mb={2}>
        個別データ ({argumentsList.length}件)
      </Text>
      <Box as="ul" pl={4} m={0} listStyleType="disc">
        {displayArguments.map((arg) => {
          const isFiltered = filteredArgumentIds && !filteredArgumentIds.includes(arg.arg_id);
          return (
            <Box as="li" key={arg.arg_id} mb={2} opacity={isFiltered ? 0.4 : 1}>
              <Text fontSize="sm" color="gray.700">
                {arg.argument}
              </Text>
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
          {showAll ? "表示を減らす" : `さらに表示 (残り${argumentsList.length - maxDisplay}件)`}
        </Box>
      )}
    </Box>
  );
}

export function HierarchyListChart({
  clusterList,
  argumentList,
  filteredArgumentIds,
  onHover,
}: HierarchyListChartProps) {
  const [treeData, setTreeData] = useState<ClusterNode[]>([]);

  // Build tree structure from flat cluster list
  useEffect(() => {
    const clusterMap = new Map<string, ClusterNode>();

    // Create nodes for all clusters
    for (const cluster of clusterList) {
      // Find arguments belonging to this cluster (at deepest level)
      const maxLevel = Math.max(...clusterList.map((c) => c.level));
      const clusterArguments =
        cluster.level === maxLevel ? argumentList.filter((arg) => arg.cluster_ids.includes(cluster.id)) : [];

      clusterMap.set(cluster.id, {
        ...cluster,
        children: [],
        isExpanded: false,
        isChildrenExpanded: false,
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

    setTreeData(sortChildren(rootNodes));
  }, [clusterList, argumentList]);

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

  // Calculate filtered state for each cluster
  const clusterFilterState = useMemo(() => {
    if (!filteredArgumentIds) return new Map<string, boolean>();

    const state = new Map<string, boolean>();
    const filteredSet = new Set(filteredArgumentIds);

    for (const cluster of clusterList) {
      const clusterArgs = argumentList.filter((arg) => arg.cluster_ids.includes(cluster.id));
      const hasMatchingArgs = clusterArgs.some((arg) => filteredSet.has(arg.arg_id));
      state.set(cluster.id, hasMatchingArgs);
    }

    return state;
  }, [clusterList, argumentList, filteredArgumentIds]);

  const renderClusterNode = (node: ClusterNode, depth = 0): ReactNode => {
    const hasChildren = node.children.length > 0;
    const hasArguments = node.arguments.length > 0;
    const hasExpandableContent = hasChildren || node.takeaway || hasArguments;

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
              aria-label={node.isExpanded ? "折りたたむ" : "展開する"}
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
            <Text fontWeight="semibold" color="gray.800" mb={1}>
              {node.label}
              <Text as="span" fontWeight="normal" fontSize="sm" color="gray.500" ml={2}>
                ({node.value}件)
              </Text>
            </Text>

            {node.isExpanded && (
              <Box mb={2}>
                {node.takeaway && (
                  <Text fontSize="sm" color="gray.600" lineHeight="1.6" mb={2}>
                    {node.takeaway}
                  </Text>
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
                      {node.isChildrenExpanded ? "子要素を閉じる" : `子要素を表示 (${node.children.length}件)`}
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
                      {node.isChildrenExpanded ? "個別データを閉じる" : `個別データを表示 (${node.arguments.length}件)`}
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
            <ArgumentsDisplay arguments={node.arguments} filteredArgumentIds={filteredArgumentIds} />
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
            階層リスト
          </Text>
          <Text fontSize="sm" color="gray.600">
            クラスタを展開して詳細を表示できます
          </Text>
        </Box>

        <Box>{treeData.map((node) => renderClusterNode(node))}</Box>
      </VStack>
    </Box>
  );
}
