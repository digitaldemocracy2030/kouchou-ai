"use client";

import { Header } from "@/components/Header";
import { toaster } from "@/components/ui/toaster";
import { Box, Button, Field, HStack, Heading, Input, Presence, Text, VStack, useDisclosure } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { type ChangeEvent, useEffect, useMemo, useState } from "react";
import { ClusterSettingsSection } from "@/app/create/components/ClusterSettingsSection";
import { AISettingsSection } from "@/app/create/components/AISettingsSection";
import { EnvironmentCheckDialog } from "@/app/create/components/EnvironmentCheckDialog/EnvironmentCheckDialog";
import { useAISettings } from "@/app/create/hooks/useAISettings";
import { useClusterSettings } from "@/app/create/hooks/useClusterSettings";
import { usePromptSettings } from "@/app/create/hooks/usePromptSettings";
import { validateReportId } from "@/app/create/utils/validation";
import { duplicateReport } from "@/app/_components/ReportCard/DuplicateReportDialog/actions";
import { getApiBaseUrl } from "@/app/utils/api";

type PageProps = {
  params: {
    slug: string;
  };
};

type ReportConfig = {
  question?: string | null;
  intro?: string | null;
  model?: string | null;
  provider?: string | null;
  is_pubcom?: boolean | null;
  is_embedded_at_local?: boolean | null;
  enable_source_link?: boolean | null;
  local_llm_address?: string | null;
  extraction?: {
    prompt?: string | null;
    workers?: number | null;
  } | null;
  hierarchical_clustering?: {
    cluster_nums?: number[] | null;
  } | null;
  hierarchical_initial_labelling?: {
    prompt?: string | null;
  } | null;
  hierarchical_merge_labelling?: {
    prompt?: string | null;
  } | null;
  hierarchical_overview?: {
    prompt?: string | null;
  } | null;
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

const formatDate = () => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
};

const toSelectEvent = (value: string) =>
  ({
    target: { value },
  }) as ChangeEvent<HTMLSelectElement>;

export default function Page({ params }: PageProps) {
  const router = useRouter();
  const { open, onToggle } = useDisclosure();
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<ReportConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  const [newSlug, setNewSlug] = useState(() => `${params.slug}-copy-${formatDate()}`);
  const [isSlugValid, setIsSlugValid] = useState(true);
  const [slugErrorMessage, setSlugErrorMessage] = useState("");
  const reuseEnabled = true;

  const [question, setQuestion] = useState("");
  const [intro, setIntro] = useState("");

  const clusterSettings = useClusterSettings();
  const promptSettings = usePromptSettings();
  const aiSettings = useAISettings();

  const modelDescription = useMemo(() => aiSettings.getModelDescription(), [aiSettings]);

  useEffect(() => {
    const controller = new AbortController();
    const loadConfig = async () => {
      setConfigError(null);
      try {
        const response = await fetch(`${getApiBaseUrl()}/admin/reports/${params.slug}/config`, {
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
        const nextConfig: ReportConfig | undefined = data?.config;
        if (!nextConfig) {
          throw new Error("設定の取得に失敗しました");
        }

        setConfig(nextConfig);
        setQuestion(nextConfig.question || "");
        setIntro(nextConfig.intro || "");

        if (nextConfig.provider) {
          aiSettings.handleProviderChange(toSelectEvent(nextConfig.provider));
        }
        if (nextConfig.model) {
          aiSettings.handleModelChange(toSelectEvent(nextConfig.model));
        }
        if (typeof nextConfig.extraction?.workers === "number") {
          aiSettings.handleWorkersChange(nextConfig.extraction.workers);
        }
        if (typeof nextConfig.is_pubcom === "boolean") {
          aiSettings.handlePubcomModeChange(nextConfig.is_pubcom);
        }
        if (typeof nextConfig.enable_source_link === "boolean") {
          aiSettings.handleEnableSourceLinkChange(nextConfig.enable_source_link);
        }
        if (typeof nextConfig.is_embedded_at_local === "boolean") {
          aiSettings.setIsEmbeddedAtLocal(nextConfig.is_embedded_at_local);
        }
        if (nextConfig.local_llm_address) {
          aiSettings.setLocalLLMAddress(nextConfig.local_llm_address);
        }

        const clusterNums = nextConfig.hierarchical_clustering?.cluster_nums || [5, 50];
        const lv1 = clusterNums[0] ?? 5;
        const lv2 = clusterNums[1] ?? Math.max(lv1 * 2, 10);
        clusterSettings.handleLv1Change(lv1);
        clusterSettings.handleLv2Change(lv2);

        promptSettings.setExtraction(nextConfig.extraction?.prompt || "");
        promptSettings.setInitialLabelling(nextConfig.hierarchical_initial_labelling?.prompt || "");
        promptSettings.setMergeLabelling(nextConfig.hierarchical_merge_labelling?.prompt || "");
        promptSettings.setOverview(nextConfig.hierarchical_overview?.prompt || "");
      } catch (error) {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setConfigError(error instanceof Error ? error.message : "設定の取得に失敗しました");
      }
    };

    loadConfig();
    return () => controller.abort();
  }, [params.slug]);

  const handleSlugChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setNewSlug(value);
    if (!value) {
      setIsSlugValid(true);
      setSlugErrorMessage("");
      return;
    }
    const validation = validateReportId(value);
    setIsSlugValid(validation.isValid);
    setSlugErrorMessage(validation.errorMessage || "");
  };

  const isSame = (value: string, original?: string | null) => value === (original ?? "");
  const isSameCluster = (lv1: number, lv2: number, original?: number[] | null) =>
    Array.isArray(original) && original[0] === lv1 && original[1] === lv2;

  const onSubmit = async () => {
    if (!config) {
      toaster.create({
        type: "error",
        title: "再利用エラー",
        description: "設定の取得に失敗したため再利用できません",
      });
      return;
    }

    if (!isSlugValid) {
      toaster.create({
        type: "error",
        title: "入力エラー",
        description: slugErrorMessage || "IDを確認してください",
      });
      return;
    }

    setLoading(true);

    const overrides: DuplicateOverrides = {};
    if (!isSame(question, config.question)) {
      overrides.question = question;
    }
    if (!isSame(intro, config.intro)) {
      overrides.intro = intro;
    }
    if (!isSame(aiSettings.provider, config.provider || "openai")) {
      overrides.provider = aiSettings.provider;
    }
    if (!isSame(aiSettings.model, config.model || "")) {
      overrides.model = aiSettings.model;
    }
    if (!isSameCluster(clusterSettings.clusterLv1, clusterSettings.clusterLv2, config.hierarchical_clustering?.cluster_nums || null)) {
      overrides.cluster = [clusterSettings.clusterLv1, clusterSettings.clusterLv2];
    }

    const promptOverride: DuplicateOverrides["prompt"] = {};
    if (!isSame(promptSettings.extraction, config.extraction?.prompt || "")) {
      promptOverride.extraction = promptSettings.extraction;
    }
    if (!isSame(promptSettings.initialLabelling, config.hierarchical_initial_labelling?.prompt || "")) {
      promptOverride.initial_labelling = promptSettings.initialLabelling;
    }
    if (!isSame(promptSettings.mergeLabelling, config.hierarchical_merge_labelling?.prompt || "")) {
      promptOverride.merge_labelling = promptSettings.mergeLabelling;
    }
    if (!isSame(promptSettings.overview, config.hierarchical_overview?.prompt || "")) {
      promptOverride.overview = promptSettings.overview;
    }
    if (Object.keys(promptOverride).length > 0) {
      overrides.prompt = promptOverride;
    }

    const result = await duplicateReport(params.slug, {
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
      router.push("/");
    } else {
      toaster.create({
        type: "error",
        title: "再利用エラー",
        description: result.error || "再利用に失敗しました",
      });
    }

    setLoading(false);
  };

  return (
    <div className={"container"}>
      <Header />
      <Box mx={"auto"} maxW={"800px"} px="6" py="12">
        <Heading textAlign={"center"} my={10}>
          レポートを再利用
        </Heading>
        <Text textAlign="center" color="gray.600" mb={8}>
          再利用元: {params.slug}
        </Text>

        <VStack gap={6} align="stretch">
          <Field.Root>
            <Field.Label>新しいID（省略可）</Field.Label>
            <Input
              w={"40%"}
              value={newSlug}
              onChange={handleSlugChange}
              placeholder={`${params.slug}-copy-YYYYMMDD`}
              aria-invalid={!isSlugValid}
              borderColor={!isSlugValid ? "red.300" : undefined}
              _hover={!isSlugValid ? { borderColor: "red.400" } : undefined}
            />
            {!isSlugValid && (
              <Text color="red.500" fontSize="sm" mt={1}>
                {slugErrorMessage}
              </Text>
            )}
            <Field.HelperText>空欄の場合は自動生成されます</Field.HelperText>
          </Field.Root>

          <Field.Root>
            <Field.Label>タイトル（省略可）</Field.Label>
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="例：人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？"
            />
            <Field.HelperText>レポートのタイトルを記載します（省略時は作成日時が使用されます）</Field.HelperText>
          </Field.Root>

          <Field.Root>
            <Field.Label>調査概要（省略可）</Field.Label>
            <Input
              value={intro}
              onChange={(e) => setIntro(e.target.value)}
              placeholder="例：このAI生成レポートは、パブリックコメントにおいて寄せられた意見に基づいています。"
            />
            <Field.HelperText>
              コメントの集計期間や、コメントの収集元など、調査の概要を記載します（省略可）
            </Field.HelperText>
          </Field.Root>

          <ClusterSettingsSection
            clusterLv1={clusterSettings.clusterLv1}
            clusterLv2={clusterSettings.clusterLv2}
            recommendedClusters={clusterSettings.recommendedClusters}
            autoAdjusted={clusterSettings.autoAdjusted}
            onLv1Change={clusterSettings.handleLv1Change}
            onLv2Change={clusterSettings.handleLv2Change}
          />

          <HStack justify={"flex-end"} w={"full"}>
            <Button onClick={onToggle} variant={"outline"}>
              レポート生成設定
            </Button>
          </HStack>

          <Presence present={open} w={"full"}>
            <AISettingsSection
              provider={aiSettings.provider}
              model={aiSettings.model}
              workers={aiSettings.workers}
              isPubcomMode={aiSettings.isPubcomMode}
              enableSourceLink={aiSettings.enableSourceLink}
              isEmbeddedAtLocal={aiSettings.isEmbeddedAtLocal}
              localLLMAddress={aiSettings.localLLMAddress}
              userApiKey={aiSettings.userApiKey}
              onProviderChange={aiSettings.handleProviderChange}
              onModelChange={aiSettings.handleModelChange}
              fetchLocalLLMModels={aiSettings.fetchLocalLLMModels}
              onWorkersChange={(e) => {
                const v = Number(e.target.value);
                if (!Number.isNaN(v)) {
                  aiSettings.handleWorkersChange(v);
                }
              }}
              onIncreaseWorkers={aiSettings.increaseWorkers}
              onDecreaseWorkers={aiSettings.decreaseWorkers}
              onPubcomModeChange={aiSettings.handlePubcomModeChange}
              onEnableSourceLinkChange={aiSettings.handleEnableSourceLinkChange}
              onUserApiKeyChange={aiSettings.handleUserApiKeyChange}
              onEmbeddedAtLocalChange={(checked) => {
                if (checked === "indeterminate") return;
                aiSettings.setIsEmbeddedAtLocal(checked);
              }}
              setLocalLLMAddress={aiSettings.setLocalLLMAddress}
              getModelDescription={() => modelDescription}
              getProviderDescription={aiSettings.getProviderDescription}
              getCurrentModels={aiSettings.getCurrentModels}
              requiresConnectionSettings={aiSettings.requiresConnectionSettings}
              isEmbeddedAtLocalDisabled={aiSettings.isEmbeddedAtLocalDisabled}
              promptSettings={promptSettings}
            />
          </Presence>

          {configError && (
            <Text color="red.500" fontSize="sm">
              {configError}
            </Text>
          )}

          <Text color="gray.500" fontSize="sm">
            入力データは再利用元から引き継がれます。
          </Text>

          <VStack mt="8" gap="6">
            <EnvironmentCheckDialog provider={aiSettings.provider} />
            <Button className={"gradientBg shadow"} size={"2xl"} w={"300px"} onClick={onSubmit} loading={loading}>
              再利用を開始
            </Button>
          </VStack>
        </VStack>
      </Box>
    </div>
  );
}
