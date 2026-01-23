import { BreadcrumbLink, BreadcrumbRoot } from "@/components/ui/breadcrumb";
import type { Cluster } from "@/type";
import { Box, Text } from "@chakra-ui/react";

type Props = {
  selectedClusters: Cluster[];
  onChangeFilter: (level1: string, level2: string, level3: string, level4: string) => void;
};

export function ClusterBreadcrumb({ selectedClusters, onChangeFilter }: Props) {
  function onChange(level: number) {
    onChangeFilter("0", "0", "0", "0");
    switch (level) {
      case 0:
        onChangeFilter("0", "0", "0", "0");
        break;
      case 1:
        onChangeFilter(selectedClusters[0].id, "0", "0", "0");
        break;
      case 2:
        onChangeFilter(selectedClusters[0].id, selectedClusters[1].id, "0", "0");
        break;
      case 3:
        onChangeFilter(selectedClusters[0].id, selectedClusters[1].id, selectedClusters[2].id, "0");
        break;
      case 4:
        // do nothing.
        break;
    }
  }

  if (!selectedClusters.length) return <></>;
  return (
    <Box mx={"auto"} maxW={"870px"} mb={6} display={{ base: "none", md: "block" }}>
      <Text fontSize={"sm"} fontWeight={"bold"}>
        表示中の意見グループ
      </Text>
      <BreadcrumbRoot size="lg">
        <BreadcrumbLink
          fontSize={"sm"}
          w={"30px"}
          onClick={() => {
            onChange(0);
          }}
          cursor={"pointer"}
        >
          全て
        </BreadcrumbLink>
        {selectedClusters.map((cluster, i) => (
          <BreadcrumbLink
            key={cluster.id}
            fontSize={"sm"}
            fontWeight={i === selectedClusters.length - 1 ? "bold" : "normal"}
            onClick={() => {
              onChange(cluster.level);
            }}
            cursor={"pointer"}
          >
            {cluster.label}
          </BreadcrumbLink>
        ))}
      </BreadcrumbRoot>
    </Box>
  );
}
