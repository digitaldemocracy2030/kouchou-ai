"use client";

import { ClusterSettingsSection } from "@/app/create/components/ClusterSettingsSection";
import { modelDescription as describeModel, modelLabel, useModelCatalog } from "@/app/create/hooks/useModelCatalog";
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
import type { Report } from "@/type";
import { Box, Button, Checkbox, HStack, Input, NativeSelect, Portal, Text, Textarea, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useMemo, useState } from "react";
import { duplicateReport } from "./actions";

type Props = {
  report: Report;
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
};

type ReportConfig = {
  question: string;
  intro: string;
  model: string;
  provider?: string | null;
  hierarchical_clustering: {
    cluster_nums: number[];
  };
  extraction: {
    prompt: string;
  };
  hierarchical_initial_labelling: {
    prompt: string;
  };
  hierarchical_merge_labelling: {
    prompt: string;
  };
  hierarchical_overview: {
    prompt: string;
  };
};

type DuplicateOverrides = {
  question?: string;
  intro?: string;
  provider?: string;
  model?: string;
  cluster?: number[];
  prompt?: {
    extraction?: string;
    initial_labelling?: string;
    merge_labelling?: string;
    overview?: string;
  };
};

export function DuplicateReportDialog({ report, isOpen, setIsOpen }: Props) {
  const router = useRouter();
  const [newSlug, setNewSlug] = useState("");
  const [reuseEnabled, setReuseEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [config, setConfig] = useState<ReportConfig | null>(null);

  const [question, setQuestion] = useState("");
  const [intro, setIntro] = useState("");
  const [provider, setProvider] = useState("openai");
  const [model, setModel] = useState("");
  const [clusterLv1, setClusterLv1] = useState(5);
  const [clusterLv2, setClusterLv2] = useState(50);
  const [autoAdjusted, setAutoAdjusted] = useState(false);
  const [recommendedClusters, setRecommendedClusters] = useState<{ lv1: number; lv2: number } | null>({
    lv1: 5,
    lv2: 50,
  });

  const [extractionPrompt, setExtractionPrompt] = useState("");
  const [initialLabellingPrompt, setInitialLabellingPrompt] = useState("");
  const [mergeLabellingPrompt, setMergeLabellingPrompt] = useState("");
  const [overviewPrompt, setOverviewPrompt] = useState("");

  const rerunSteps = useMemo(() => {
    if (!reuseEnabled) {
      return "extraction → embedding → clustering → overview";
    }
    return "overview";
  }, [reuseEnabled]);

  const catalog = useModelCatalog(provider, undefined, isOpen && provider !== "local");
  const selectedModel = catalog.models.find((option) => option.value === model);
  const modelOptions =
    model && !selectedModel ? [{ value: model, label: model, available: false }, ...catalog.models] : catalog.models;
  const modelError =
    provider === "local"
      ? !model
        ? "モデルを入力してください。"
        : ""
      : catalog.loading
        ? "モデル一覧を取得中です。"
        : catalog.error ||
          (provider !== "azure" && (!selectedModel || selectedModel.available === false)
            ? "このモデルは利用できません。モデルを再選択してください。"
            : "");
  const modelDescription = modelError || describeModel(provider === "azure" ? catalog.models[0] : selectedModel);
  useEffect(() => {
    if (!model && catalog.models.length)
      setModel(catalog.models.find((option) => option.available !== false)?.value || "");
  }, [catalog.models, model]);

  useEffect(() => {
    if (!isOpen) {
      setConfig(null);
      setConfigError(null);
      return;
    }

    const controller = new AbortController();
    const loadConfig = async () => {
      setIsLoadingConfig(true);
      setConfigError(null);
      try {
        const response = await fetch(`/api/admin/reports/${report.slug}/config`, {
          signal: controller.signal,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || "設定の取得に失敗しました");
        }

        const data = await response.json();
        const nextConfig: ReportConfig = data?.config;
        if (!nextConfig) {
          throw new Error("設定の取得に失敗しました");
        }

        setConfig(nextConfig);
        setQuestion(nextConfig.question || "");
        setIntro(nextConfig.intro || "");
        setProvider(nextConfig.provider || "openai");
        setModel(nextConfig.model || "");
        const clusterNums = nextConfig.hierarchical_clustering?.cluster_nums || [5, 50];
        const lv1 = clusterNums[0] ?? 5;
        const lv2 = clusterNums[1] ?? Math.max(lv1 * 2, 10);
        setClusterLv1(lv1);
        setClusterLv2(lv2);
        setRecommendedClusters({ lv1, lv2 });
        setAutoAdjusted(false);
        setExtractionPrompt(nextConfig.extraction?.prompt || "");
        setInitialLabellingPrompt(nextConfig.hierarchical_initial_labelling?.prompt || "");
        setMergeLabellingPrompt(nextConfig.hierarchical_merge_labelling?.prompt || "");
        setOverviewPrompt(nextConfig.hierarchical_overview?.prompt || "");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setConfigError(error instanceof Error ? error.message : "設定の取得に失敗しました");
      } finally {
        setIsLoadingConfig(false);
      }
    };

    loadConfig();
    return () => controller.abort();
  }, [isOpen, report.slug]);

  const isSame = (value: string, original?: string | null) => value === (original ?? "");
  const isSameCluster = (lv1: number, lv2: number, original?: number[]) =>
    Array.isArray(original) && original[0] === lv1 && original[1] === lv2;

  const handleLv1Change = (value: number) => {
    const limitedValue = Math.max(2, Math.min(40, value));
    setClusterLv1(limitedValue);
    const newLv2 = limitedValue * 2;
    if (newLv2 > clusterLv2) {
      setClusterLv2(newLv2);
      setAutoAdjusted(true);
    } else {
      setAutoAdjusted(false);
    }
    setRecommendedClusters({ lv1: limitedValue, lv2: newLv2 > clusterLv2 ? newLv2 : clusterLv2 });
  };

  const handleLv2Change = (value: number) => {
    let limitedValue = Math.max(2, Math.min(1000, value));
    if (limitedValue < clusterLv1 * 2) {
      limitedValue = clusterLv1 * 2;
      setAutoAdjusted(true);
    } else {
      setAutoAdjusted(false);
    }
    setClusterLv2(limitedValue);
    setRecommendedClusters({ lv1: clusterLv1, lv2: limitedValue });
  };

  const renderLabel = (label: string, reused: boolean) => (
    <Box as="span" display="inline-flex" alignItems="center" justifyContent="space-between" w="full">
      <Box as="span">{label}</Box>
      {reused && (
        <Box as="span" color="gray.500" fontSize="xs">
          再利用
        </Box>
      )}
    </Box>
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    if (!config) {
      toaster.create({
        type: "error",
        title: "再利用エラー",
        description: "設定の取得に失敗したため再利用できません",
      });
      return;
    }

    if (modelError) {
      toaster.create({ type: "error", title: modelError });
      return;
    }
    setIsSubmitting(true);

    try {
      const overrides: DuplicateOverrides = {};
      if (!isSame(question, config.question)) {
        overrides.question = question;
      }
      if (!isSame(intro, config.intro)) {
        overrides.intro = intro;
      }
      if (!isSame(provider, config.provider || "openai")) {
        overrides.provider = provider;
      }
      if (!isSame(model, config.model)) {
        overrides.model = model;
      }
      if (!isSameCluster(clusterLv1, clusterLv2, config.hierarchical_clustering?.cluster_nums)) {
        overrides.cluster = [clusterLv1, clusterLv2];
      }

      const promptOverride: DuplicateOverrides["prompt"] = {};
      if (!isSame(extractionPrompt, config.extraction?.prompt)) {
        promptOverride.extraction = extractionPrompt;
      }
      if (!isSame(initialLabellingPrompt, config.hierarchical_initial_labelling?.prompt)) {
        promptOverride.initial_labelling = initialLabellingPrompt;
      }
      if (!isSame(mergeLabellingPrompt, config.hierarchical_merge_labelling?.prompt)) {
        promptOverride.merge_labelling = mergeLabellingPrompt;
      }
      if (!isSame(overviewPrompt, config.hierarchical_overview?.prompt)) {
        promptOverride.overview = overviewPrompt;
      }
      if (Object.keys(promptOverride).length > 0) {
        overrides.prompt = promptOverride;
      }

      const result = await duplicateReport(report.slug, {
        newSlug: newSlug.trim() || undefined,
        reuseEnabled,
        overrides: Object.keys(overrides).length > 0 ? overrides : undefined,
      });

      if (result.success) {
        toaster.create({
          type: "success",
          title: "再利用を開始しました",
          description: `新しいレポート: ${result.slug}`,
        });
        setIsOpen(false);
        setNewSlug("");
        setReuseEnabled(true);
        router.refresh();
      } else {
        toaster.create({
          type: "error",
          title: "再利用エラー",
          description: result.error || "再利用に失敗しました",
        });
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "再利用に失敗しました";
      toaster.create({
        type: "error",
        title: "再利用エラー",
        description: message,
      });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <DialogRoot placement="center" open={isOpen} onOpenChange={({ open }) => setIsOpen(open)}>
      <Portal>
        <DialogBackdrop />
        <DialogContent maxW="800px" w="full">
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader>
            <DialogTitle>レポートを再利用</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <DialogBody maxH="70vh" overflowY="scroll" pr={4}>
              <VStack gap={4} align="stretch">
                <Text fontSize="sm" color="gray.500">
                  変更されていない項目は再利用されます。可視性は再利用時に非公開（unlisted）で作成されます。
                </Text>
                <Box>
                  <Text mb={2} fontWeight="bold">
                    新しいslug (任意)
                  </Text>
                  <Input
                    value={newSlug}
                    onChange={(event) => setNewSlug(event.target.value)}
                    placeholder={`${report.slug}-copy-YYYYMMDD`}
                  />
                  <Text fontSize="sm" color="gray.500" mt={1}>
                    空欄の場合は自動生成されます
                  </Text>
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel("タイトル", config ? isSame(question, config.question) : false)}
                  </Box>
                  <Input value={question} onChange={(event) => setQuestion(event.target.value)} />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel("調査概要", config ? isSame(intro, config.intro) : false)}
                  </Box>
                  <Textarea value={intro} onChange={(event) => setIntro(event.target.value)} />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel("AIプロバイダー", config ? isSame(provider, config.provider || "openai") : false)}
                  </Box>
                  <NativeSelect.Root w={"60%"}>
                    <NativeSelect.Field
                      value={provider}
                      onChange={(e) => {
                        const nextProvider = e.target.value;
                        setProvider(nextProvider);
                        setModel("");
                      }}
                    >
                      <option value={"openai"}>OpenAI</option>
                      <option value={"azure"}>Azure</option>
                      <option value={"openrouter"}>OpenRouter</option>
                      <option value={"gemini"}>Gemini</option>
                      <option value={"local"}>LocalLLM</option>
                    </NativeSelect.Field>
                    <NativeSelect.Indicator />
                  </NativeSelect.Root>
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel("AIモデル", config ? isSame(model, config.model) : false)}
                  </Box>
                  {provider === "local" ? (
                    <Input value={model} onChange={(event) => setModel(event.target.value)} />
                  ) : (
                    <NativeSelect.Root w="full" disabled={provider === "azure"}>
                      <NativeSelect.Field
                        value={provider === "azure" ? "azure-server" : model}
                        onChange={(e) => setModel(e.target.value)}
                      >
                        {modelOptions.map((option) => (
                          <option key={option.value} value={option.value} disabled={option.available === false}>
                            {provider === "azure" ? option.label : modelLabel(option)}
                          </option>
                        ))}
                      </NativeSelect.Field>
                      <NativeSelect.Indicator />
                    </NativeSelect.Root>
                  )}
                  {catalog.models[0]?.discovery_warning && <Text>{catalog.models[0].discovery_warning}</Text>}
                  {provider !== "local" && (
                    <Button onClick={catalog.reload} variant="outline">
                      モデル一覧を再取得
                    </Button>
                  )}
                  {modelDescription && (
                    <Text color="gray.500" fontSize="sm" mt={1}>
                      {modelDescription}
                    </Text>
                  )}
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel(
                      "意見グループ数設定",
                      config
                        ? isSameCluster(clusterLv1, clusterLv2, config.hierarchical_clustering?.cluster_nums)
                        : false,
                    )}
                  </Box>
                  <ClusterSettingsSection
                    clusterLv1={clusterLv1}
                    clusterLv2={clusterLv2}
                    recommendedClusters={recommendedClusters}
                    autoAdjusted={autoAdjusted}
                    onLv1Change={handleLv1Change}
                    onLv2Change={handleLv2Change}
                  />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel(
                      "抽出プロンプト",
                      config ? isSame(extractionPrompt, config.extraction?.prompt) : false,
                    )}
                  </Box>
                  <Textarea
                    h={"150px"}
                    value={extractionPrompt}
                    onChange={(event) => setExtractionPrompt(event.target.value)}
                    aria-label="抽出プロンプト"
                  />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel(
                      "初期ラベリングプロンプト",
                      config ? isSame(initialLabellingPrompt, config.hierarchical_initial_labelling?.prompt) : false,
                    )}
                  </Box>
                  <Textarea
                    h={"150px"}
                    value={initialLabellingPrompt}
                    onChange={(event) => setInitialLabellingPrompt(event.target.value)}
                    aria-label="初期ラベリングプロンプト"
                  />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel(
                      "統合ラベリングプロンプト",
                      config ? isSame(mergeLabellingPrompt, config.hierarchical_merge_labelling?.prompt) : false,
                    )}
                  </Box>
                  <Textarea
                    h={"150px"}
                    value={mergeLabellingPrompt}
                    onChange={(event) => setMergeLabellingPrompt(event.target.value)}
                    aria-label="統合ラベリングプロンプト"
                  />
                </Box>
                <Box>
                  <Box mb={2} fontWeight="bold">
                    {renderLabel(
                      "要約プロンプト",
                      config ? isSame(overviewPrompt, config.hierarchical_overview?.prompt) : false,
                    )}
                  </Box>
                  <Textarea
                    h={"150px"}
                    value={overviewPrompt}
                    onChange={(event) => setOverviewPrompt(event.target.value)}
                    aria-label="要約プロンプト"
                  />
                </Box>
                <Box>
                  <Checkbox.Root checked={reuseEnabled} onCheckedChange={(e) => setReuseEnabled(!!e.checked)}>
                    <Checkbox.HiddenInput />
                    <Checkbox.Control />
                    <Checkbox.Label>中間成果物を再利用する</Checkbox.Label>
                  </Checkbox.Root>
                  <Text color="gray.500" fontSize="sm" mt={1}>
                    OFFにすると extraction から再実行されます
                  </Text>
                </Box>
                {configError && (
                  <Text color="red.500" fontSize="sm">
                    {configError}
                  </Text>
                )}
                <Box>
                  <Text fontWeight="bold" mb={1}>
                    再実行されるステップ
                  </Text>
                  <Text color="gray.600">{rerunSteps}</Text>
                  <Text color="gray.500" fontSize="sm" mt={1}>
                    再利用時は overview を常に再生成します
                  </Text>
                </Box>
              </VStack>
            </DialogBody>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                キャンセル
              </Button>
              <Button
                ml={3}
                type="submit"
                loading={isSubmitting}
                disabled={!config || isLoadingConfig || !!configError}
              >
                再利用を開始
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
