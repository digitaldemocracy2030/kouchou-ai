"use client";

import {
  DialogBackdrop,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog";
import { toaster } from "@/components/ui/toaster";
import type { ClusterResponse, Report } from "@/type";
import {
  Box,
  Button,
  Heading,
  Input,
  Portal,
  Select,
  Separator,
  Text,
  Textarea,
  VStack,
  createListCollection,
} from "@chakra-ui/react";
import { type Dispatch, type SetStateAction, useCallback, useEffect, useMemo, useState } from "react";
import { fetchClusters, updateCluster } from "./actions";

type ClusterEditDialogProps = {
  report: Report;
  isOpen: boolean;
  setIsClusterEditDialogOpen: Dispatch<SetStateAction<boolean>>;
};

export function ClusterEditDialog({ report, isOpen, setIsClusterEditDialogOpen }: ClusterEditDialogProps) {
  const [clusters, setClusters] = useState<ClusterResponse[]>([]);

  const fetchInitialClusters = useCallback(async () => {
    const result = await fetchClusters(report.slug);
    if (!result.success) {
      toaster.create({
        type: "error",
        title: "エラー",
        description: "クラスタ一覧の取得に失敗しました。",
      });
      return;
    }
    setClusters(result.clusters);
  }, [report.slug]);

  useEffect(() => {
    if (isOpen) {
      fetchInitialClusters();
    } else {
      setClusters([]);
    }
  }, [fetchInitialClusters, isOpen]);

  return (
    clusters.length > 0 && (
      <Dialog clusters={clusters} report={report} isOpen={isOpen} setIsOpen={setIsClusterEditDialogOpen} />
    )
  );
}

type DialogProps = {
  clusters: ClusterResponse[];
  report: Report;
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
};

function Dialog({ clusters, report, isOpen, setIsOpen }: DialogProps) {
  const sortedCluster = [...clusters].sort((a, b) => b.value - a.value);
  const firstCluster = sortedCluster[0];
  const [selectedClusterId, setSelectedClusterId] = useState<string>(firstCluster.id);
  const [selectedLevel, setSelectedLevel] = useState<number>(1); // デフォルトの階層は1

  const selectedCluster = sortedCluster.find((c) => c.id === selectedClusterId) || firstCluster;
  const editClusterTitle = selectedCluster.label;
  const editClusterDescription = selectedCluster.description;

  // 意見グループの階層を取得
  const availableLevels = useMemo(() => {
    const levels = [...new Set(clusters.map((c) => c.level))].sort((a, b) => a - b);
    return levels.length > 0 ? levels : [1];
  }, [clusters]);
  const argumentsCollection = createListCollection({
    items: availableLevels.map((level) => ({ label: `第${level}階層`, value: String(level) })),
  });

  // 選択された階層の意見グループのみをフィルタリング
  const filteredClustersCollection = createListCollection({
    items: sortedCluster.filter((c) => c.level === selectedLevel).map((c) => ({ label: c.label, value: c.id })),
  });

  async function handleSubmit(formData: FormData) {
    const result = await updateCluster(report.slug, formData);

    if (!result.success) {
      toaster.create({
        type: "error",
        title: "更新エラー",
        description: result.error || "意見グループ情報の更新に失敗しました",
      });
      return;
    }

    toaster.create({
      type: "success",
      title: "更新完了",
      description: "意見グループ情報が更新されました",
    });

    setIsOpen(false);
  }

  return (
    <DialogRoot placement="center" open={isOpen} modal={true} closeOnInteractOutside={true} trapFocus={true}>
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader>
            <DialogTitle>意見グループを編集</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <form action={handleSubmit} id="cluster-edit-form">
              <VStack gap={4} align="stretch">
                <Heading size="md">編集対象の選択</Heading>
                <Box>
                  <Text mb={2} fontWeight="bold">
                    意見グループの階層
                  </Text>
                  <Select.Root
                    collection={argumentsCollection}
                    defaultValue={[String(selectedLevel)]}
                    onValueChange={(item) => {
                      const level = Number(item.value[0]);
                      setSelectedLevel(level);
                      const c = clusters.find((c) => c.level === level);
                      if (!c) return;
                      setSelectedClusterId(c.id);
                    }}
                  >
                    <Select.HiddenSelect />
                    <Select.Control>
                      <Select.Trigger>
                        <Select.ValueText placeholder="階層を選択" />
                      </Select.Trigger>
                      <Select.IndicatorGroup>
                        <Select.Indicator />
                      </Select.IndicatorGroup>
                    </Select.Control>
                    <Select.Positioner>
                      <Select.Content>
                        {argumentsCollection.items.map((item) => (
                          <Select.Item item={item} key={item.value}>
                            {item.label}
                            <Select.ItemIndicator />
                          </Select.Item>
                        ))}
                      </Select.Content>
                    </Select.Positioner>
                  </Select.Root>
                </Box>
                <Box>
                  <Text mb={2} fontWeight="bold">
                    編集対象のグループ
                  </Text>
                  <Select.Root
                    name="id"
                    collection={filteredClustersCollection}
                    key={selectedLevel}
                    defaultValue={[filteredClustersCollection.items[0].value]}
                    onValueChange={(item) => {
                      const selected = clusters.find((c) => c.id === item.value[0]);
                      if (!selected) return;
                      setSelectedClusterId(selected.id);
                    }}
                  >
                    <Select.HiddenSelect />
                    <Select.Control>
                      <Select.Trigger>
                        <Select.ValueText placeholder="意見グループを選択" />
                      </Select.Trigger>
                      <Select.IndicatorGroup>
                        <Select.Indicator />
                      </Select.IndicatorGroup>
                    </Select.Control>
                    <Select.Positioner>
                      <Select.Content>
                        {filteredClustersCollection.items.map((item) => (
                          <Select.Item item={item} key={item.value}>
                            {item.label}
                            <Select.ItemIndicator />
                          </Select.Item>
                        ))}
                      </Select.Content>
                    </Select.Positioner>
                  </Select.Root>
                </Box>
                <Separator my={4} />
                <Heading size="md">意見グループの編集</Heading>
                <VStack gap={4} align="stretch">
                  <Box>
                    <Text mb={2} fontWeight="bold">
                      タイトル
                    </Text>
                    <Input
                      key={selectedClusterId}
                      name="label"
                      defaultValue={editClusterTitle}
                      placeholder="タイトルを入力"
                      required
                    />
                  </Box>
                  <Box>
                    <Text mb={2} fontWeight="bold">
                      説明
                    </Text>
                    <Textarea
                      key={selectedClusterId}
                      name="description"
                      defaultValue={editClusterDescription}
                      placeholder="説明を入力"
                      height="150px"
                      required
                    />
                  </Box>
                </VStack>
              </VStack>
            </form>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsOpen(false)}>
              キャンセル
            </Button>
            <Button type="submit" form="cluster-edit-form">
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
