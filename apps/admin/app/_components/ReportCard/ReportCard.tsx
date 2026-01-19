import type { Report } from "@/type";
import { GridItem, HStack, IconButton, Text } from "@chakra-ui/react";
import { Bot, LinkIcon } from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import Link from "next/link";
import { useState } from "react";
import { ActionMenu } from "./ActionMenu/ActionMenu";
import { ClusterEditDialog } from "./ClusterEditDialog/ClusterEditDialog";
import { DeleteButton } from "./DeleteButton";
import { NumberDisplay } from "./NumberDisplay";
import { ProgressSteps } from "./ProgressSteps/ProgressSteps";
import { ReportCreatedAt } from "./ReportCreatedAt";
import { ReportEditDialog } from "./ReportEditDialog/ReportEditDialog";
import { ReportTitle } from "./ReportTitle";
import { TokenUsage } from "./TokenUsage/TokenUsage";
import { Visibility } from "./Visibility/Visibility";

type Props = {
  report: Report;
};

const duration = 0.3;

function ReportDataAndActions({ report }: Props) {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isClusterEditDialogOpen, setIsClusterEditDialogOpen] = useState(false);
  return (
    <LayoutGroup>
      <AnimatePresence mode="wait">
        {report.status === "ready" && (
          <motion.div
            layout="position"
            key={`${report.slug}-${report.status}`}
            layoutId={`middle-${report.slug}`}
            transition={{ duration }}
            initial={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ display: "grid", gridTemplateColumns: "subgrid", gridColumn: "span 7", alignItems: "center" }}
          >
            <GridItem>
              <IconButton variant="ghost" size="lg" _hover={{ bg: "blue.50", boxShadow: "none" }} asChild>
                <Link
                  href={`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <LinkIcon />
                </Link>
              </IconButton>
            </GridItem>
            <GridItem>
              <NumberDisplay value={report.analysis?.commentNum} />
            </GridItem>
            <GridItem>
              <NumberDisplay value={report.analysis?.argumentsNum} />
            </GridItem>
            <GridItem>
              <NumberDisplay value={report.analysis?.clusterNum} />
            </GridItem>
            <GridItem>
              <TokenUsage report={report} />
            </GridItem>
            <GridItem>
              <ActionMenu
                report={report}
                setIsEditDialogOpen={setIsEditDialogOpen}
                setIsClusterEditDialogOpen={setIsClusterEditDialogOpen}
              />
            </GridItem>
            <GridItem>
              <Visibility report={report} />
            </GridItem>
            <ReportEditDialog
              isEditDialogOpen={isEditDialogOpen}
              setIsEditDialogOpen={setIsEditDialogOpen}
              report={report}
            />
            <ClusterEditDialog
              report={report}
              isOpen={isClusterEditDialogOpen}
              setIsClusterEditDialogOpen={setIsClusterEditDialogOpen}
            />
          </motion.div>
        )}
        {report.status === "processing" && (
          <motion.div
            layout="position"
            key={`${report.slug}-${report.status}`}
            layoutId={`middle-${report.slug}`}
            transition={{ duration }}
            initial={{ opacity: 0 }}
            exit={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            style={{ display: "flex", alignItems: "center", height: "100%", gridColumn: "span 7", marginLeft: "4px" }}
          >
            <HStack color="font.processing">
              <Bot />
              <Text textStyle="body/sm/bold">AIによるレポート作成中です。完了までしばらくお待ちください。</Text>
            </HStack>
          </motion.div>
        )}
        {report.status === "error" && (
          <>
            <motion.div
              layout="position"
              key={`${report.slug}-${report.status}`}
              layoutId={`middle-${report.slug}`}
              transition={{ duration }}
              initial={{ opacity: 0 }}
              exit={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              style={{ display: "flex", alignItems: "center", height: "100%", gridColumn: "span 6", marginLeft: "4px" }}
            >
              <HStack color="font.error">
                <Bot />
                <Text textStyle="body/sm/bold">エラーが発生しました。レポート生成設定を調整してください。</Text>
              </HStack>
            </motion.div>
            <DeleteButton report={report} />
          </>
        )}
      </AnimatePresence>
    </LayoutGroup>
  );
}

export function ReportCard({ report }: Props) {
  return (
    <>
      <GridItem>
        <ReportCreatedAt createdAt={report.createdAt} />
      </GridItem>
      <GridItem ml="2">
        <ReportTitle report={report} />
      </GridItem>
      {<ReportDataAndActions report={report} />}
      <AnimatePresence>
        {(report.status === "processing" || report.status === "error") && (
          <motion.div
            transition={{
              opacity: { duration },
              height: { duration, delay: duration },
            }}
            style={{ display: "grid", gridColumn: "span 9", marginTop: "12px" }}
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, height: 0 }}
          >
            <ProgressSteps slug={report.slug} />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
