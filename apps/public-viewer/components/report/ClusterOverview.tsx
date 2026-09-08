import type { Cluster } from "@/type";
import { Box, Heading, Link, Text } from "@chakra-ui/react";
import { MessagesSquareIcon } from "lucide-react";

type Props = {
  cluster: Cluster;
  onNavigate?: () => void;
};

export function ClusterOverview({ cluster, onNavigate }: Props) {
  return (
    <Box mx={"auto"} maxW={"750px"} mb={12}>
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
          {cluster.value.toLocaleString()}件
        </Text>
      </Box>
      <Text>{cluster.takeaway}</Text>
    </Box>
  );
}
