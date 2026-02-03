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
import type { Report } from "@/type";
import { ClusterSettingsSection } from "@/app/create/components/ClusterSettingsSection";
import { Checkbox } from "@/components/ui/checkbox";
import { Box, Button, HStack, Input, NativeSelect, Portal, Text, Textarea, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { type Dispatch, type FormEvent, type SetStateAction, useEffect, useMemo, useState } from "react";
import { duplicateReport } from "./actions";
import { getApiBaseUrl } from "@/app/utils/api";

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

  const getModelOptions = (nextProvider: string, currentModel: string) => {
    if (nextProvider === "openrouter") {
      return [
        { value: "openai/gpt-4o-2024-08-06", label: "GPT-4o (OpenRouter)" },
        { value: "openai/gpt-4o-mini-2024-07-18", label: "GPT-4o mini (OpenRouter)" },
        { value: "google/gemini-2.5-pro-preview", label: "Gemini 2.5 Pro" },
      ];
    }
    if (nextProvider === "gemini") {
      return [
        { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
        { value: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
        { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
      ];
    }
    if (nextProvider === "local") {
      return currentModel ? [{ value: currentModel, label: currentModel }] : [];
    }
    return [
      { value: "gpt-4o-mini", label: "GPT-4o mini" },
      { value: "gpt-4o", label: "GPT-4o" },
      { value: "o3-mini", label: "o3-mini" },
    ];
  };

  const modelOptions = useMemo(() => getModelOptions(provider, model), [provider, model]);

  const modelDescription = useMemo(() => {
    if (provider === "openai" || provider === "azure") {
      if (model === "gpt-4o-mini") {
        return "GPT-4o mini：最も安価に利用できるモデルです。価格の詳細はOpenAIが公開しているAPI料金のページをご参照ください。";
      }
      if (model === "gpt-4o") {
        return "GPT-4o：gpt-4o-miniと比較して高性能なモデルです。性能は高くなりますが、gpt-4o-miniと比較してOpenAI APIの料金は高くなります。";
      }
      if (model === "o3-mini") {
        return "o3-mini：gpt-4oよりも高度な推論能力を備えたモデルです。性能はより高くなりますが、gpt-4oと比較してOpenAI APIの料金は高くなります。";
      }
    }
    if (provider === "gemini") {
      if (model === "gemini-2.5-flash") {
        return "Gemini 1.5 Flash：高速かつコスト効率の高いモデルです。価格の詳細はGoogleが公開しているAPI料金のページをご参照ください。";
      }
      if (model === "gemini-1.5-flash") {
        return "Gemini 1.5 Flash：旧モデルです。価格の詳細はGoogleが公開しているAPI料金のページをご参照ください。";
      }
      if (model === "gemini-1.5-pro") {
        return "Gemini 1.5 Pro：Gemini 1.5 Flashよりも高度な推論能力を備えたモデルです。性能はより高くなりますが、Gemini 1.5 Flashと比較してAPIの料金は高くなります。";
      }
    }
    return "";
  }, [provider, model]);

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
        const response = await fetch(`${getApiBaseUrl()}/admin/reports/${report.slug}/config`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
          },
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
        title: "複製エラー",
        description: "設定の取得に失敗したため複製できません",
      });
      return;
    }

    setIsSubmitting(true);

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
        title: "複製を開始しました",
        description: `新しいレポート: ${result.slug}`,
      });
      setIsOpen(false);
      setNewSlug("");
      setReuseEnabled(true);
      router.refresh();
    } else {
      toaster.create({
        type: "error",
        title: "複製エラー",
        description: result.error || "複製に失敗しました",
      });
    }

    setIsSubmitting(false);
  }

  return (
    <DialogRoot placement="center" open={isOpen} onOpenChange={({ open }) => setIsOpen(open)}>
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader>
            <DialogTitle>レポートを複製</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <DialogBody>
              <VStack gap={4} align="stretch">
                <Text fontSize="sm" color="gray.500">
                  変更されていない項目は再利用されます。可視性は複製時に非公開（unlisted）で作成されます。
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
                      if (nextProvider !== "local") {
                        const options = getModelOptions(nextProvider, model);
                        if (options.length > 0) {
                          setModel(options[0].value);
                        }
                      }
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
                    <NativeSelect.Root w={"60%"}>
                      <NativeSelect.Field value={model} onChange={(e) => setModel(e.target.value)}>
                        {modelOptions.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </NativeSelect.Field>
                      <NativeSelect.Indicator />
                    </NativeSelect.Root>
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
                      config ? isSameCluster(clusterLv1, clusterLv2, config.hierarchical_clustering?.cluster_nums) : false,
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
                  <Checkbox
                    checked={reuseEnabled}
                    onCheckedChange={(details) => {
                      if (details.checked === "indeterminate") return;
                      setReuseEnabled(details.checked);
                    }}
                  >
                    中間成果物を再利用する
                  </Checkbox>
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
                    複製時は overview を常に再生成します
                  </Text>
                </Box>
              </VStack>
            </DialogBody>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                キャンセル
              </Button>
              <Button ml={3} type="submit" loading={isSubmitting} disabled={isLoadingConfig || !!configError}>
                複製を開始
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
