import type { Report } from "@/type";
import { Grid, GridItem } from "@chakra-ui/react";
import { Empty } from "./Empty";
import { ReportCard } from "./ReportCard/ReportCard";

type Props = {
  reports: Report[];
};

export function ReportCardList({ reports }: Props) {
  return (
    <Grid
      gridTemplateColumns="170px minmax(330px, 1fr) 52px repeat(3, minmax(83px, min-content)) repeat(3, minmax(52px, min-content))"
      rowGap="2"
    >
      <Grid px="6" gridTemplateColumns="subgrid" columnGap="2" gridColumn="span 9" bg="blue.100" textStyle="body/sm">
        <GridItem py="3" borderLeftRadius="sm">
          作成日時
        </GridItem>
        <GridItem py="3">レポート名</GridItem>
        <GridItem />
        <GridItem py="3" textAlign="center">
          コメント
        </GridItem>
        <GridItem py="3" textAlign="center">
          意見
        </GridItem>
        <GridItem py="3" textAlign="center">
          意見グループ
        </GridItem>
        <GridItem py="3" />
        <GridItem py="3" />
        <GridItem py="3" borderRightRadius="sm" />
      </Grid>
      {reports.length === 0 ? (
        <Grid gridColumn="span 9">
          <Empty />
        </Grid>
      ) : (
        reports.map((report) => (
          <Grid
            key={report.slug}
            p="6"
            gridTemplateColumns="subgrid"
            gridTemplateRows="44px auto"
            gridColumn="span 9"
            columnGap="2"
            bgColor="white"
            borderRadius="sm"
            color="font.primary"
            alignItems="center"
            _hover={{
              shadow: "lg",
            }}
          >
            <ReportCard report={report} />
          </Grid>
        ))
      )}
    </Grid>
  );
}
