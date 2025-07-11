import type { Report } from "@/type";
import { Grid, GridItem } from "@chakra-ui/react";
import { ReportCard } from "./ReportCard/ReportCard";

type Props = {
  reports: Report[];
  setReports: React.Dispatch<React.SetStateAction<Report[]>>;
};

export function ReportCardList({ reports, setReports }: Props) {
  return (
    <Grid gridTemplateColumns="170px minmax(300px, 1fr) 52px repeat(3, 83px) repeat(3, min-content)" rowGap="2">
      <Grid gridTemplateColumns="subgrid" gridColumn="span 9" textStyle="body/sm">
        <GridItem bg="blue.100" py="3" px="6" borderLeftRadius="sm">
          作成日時
        </GridItem>
        <GridItem bg="blue.100" py="3">
          レポート名
        </GridItem>
        <GridItem bg="blue.100" />
        <GridItem bg="blue.100" py="3" textAlign="center">
          コメント
        </GridItem>
        <GridItem bg="blue.100" py="3" textAlign="center">
          意見
        </GridItem>
        <GridItem bg="blue.100" py="3" textAlign="center">
          意見グループ
        </GridItem>
        <GridItem bg="blue.100" py="3" />
        <GridItem bg="blue.100" py="3" />
        <GridItem bg="blue.100" py="3" borderRightRadius="sm" />
      </Grid>
      {reports.map((report) => (
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
          <ReportCard report={report} reports={reports} setReports={setReports} />
        </Grid>
      ))}
    </Grid>
  );
}
