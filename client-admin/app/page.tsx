"use client";

import { getApiBaseUrl } from "@/app/utils/api";
import { Header } from "@/components/Header";
import { ClusterEditDialog } from "@/components/dialogs/ClusterEditDialog";
import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "@/components/ui/menu";
import { toaster } from "@/components/ui/toaster";
import { Tooltip } from "@/components/ui/tooltip";
import type { ClusterResponse, Report } from "@/type";
import {
  Box,
  Button,
  Card,
  Dialog,
  Flex,
  HStack,
  Heading,
  Icon,
  Image,
  Input,
  LinkBox,
  LinkOverlay,
  Popover,
  Portal,
  Select,
  Spinner,
  Steps,
  Text,
  Textarea,
  VStack,
  createListCollection,
} from "@chakra-ui/react";
import {
  CircleAlertIcon,
  CircleCheckIcon,
  CircleFadingArrowUpIcon,
  DownloadIcon,
  EllipsisIcon,
  ExternalLinkIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

// ステップの定義
const stepKeys = [
  "extraction",
  "embedding",
  "hierarchical_clustering",
  "hierarchical_initial_labelling",
  "hierarchical_merge_labelling",
  "hierarchical_overview",
  "hierarchical_aggregation",
  "hierarchical_visualization",
];

const steps = [
  { id: 1, title: "抽出", description: "データの抽出" },
  { id: 2, title: "埋め込み", description: "埋め込み表現の生成" },
  { id: 3, title: "意見グループ化", description: "意見グループ化の実施" },
  { id: 4, title: "初期ラベリング", description: "初期ラベルの付与" },
  { id: 5, title: "統合ラベリング", description: "ラベルの統合" },
  { id: 6, title: "概要生成", description: "概要の作成" },
  { id: 7, title: "集約", description: "結果の集約" },
  { id: 8, title: "可視化", description: "結果の可視化" },
];

// ステータスに応じた表示内容を返す関数
function getStatusDisplay(status: string) {
  switch (status) {
    case "ready":
      return {
        borderColor: "green",
        iconColor: "green",
        textColor: "#2577b1",
        icon: <CircleCheckIcon size={30} />,
      };
    case "error":
      return {
        borderColor: "red.600",
        iconColor: "red.600",
        textColor: "red.600",
        icon: <CircleAlertIcon size={30} />,
      };
    default:
      return {
        borderColor: "gray",
        iconColor: "gray",
        textColor: "gray",
        icon: <CircleFadingArrowUpIcon size={30} />,
      };
  }
}

// カスタムフック：fetchを用いて指定レポートの進捗を定期ポーリングで取得
function useReportProgressPoll(slug: string, shouldSubscribe: boolean) {
  const [progress, setProgress] = useState<string>("loading");
  const [errorStep, setErrorStep] = useState<string | null>(null);
  const [lastValidStep, setLastValidStep] = useState<string>("loading");
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [tokenUsage, setTokenUsage] = useState<number>(0);
  const [tokenUsageInput, setTokenUsageInput] = useState<number>(0);
  const [tokenUsageOutput, setTokenUsageOutput] = useState<number>(0);
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const [provider, setProvider] = useState<string | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const [pricingData, setPricingData] = useState<Record<string, Record<string, { input: number; output: number }>>>({});
  const [isPricingLoaded, setIsPricingLoaded] = useState<boolean>(false);

  // LLM価格情報を取得する
  useEffect(() => {
    async function fetchPricingData() {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/llm-pricing`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Pragma: "no-cache",
          },
        });

        if (response.ok) {
          const data = await response.json();
          setPricingData(data);
        } else {
          console.error("Failed to fetch LLM pricing data");
          // APIから取得できない場合は空のオブジェクトを設定（情報なし）
          setPricingData({});
        }
        setIsPricingLoaded(true);
      } catch (error) {
        console.error("Error fetching LLM pricing data:", error);
        setIsPricingLoaded(true);
      }
    }

    fetchPricingData();
  }, []);


  // トークン使用量から推定コストを計算する関数
  const calculateCost = (
    provider: string | null,
    model: string | null,
    tokenUsageInput: number,
    tokenUsageOutput: number
  ): number => {
    if (!provider || !model || !isPricingLoaded) return 0;
    
    const price = pricingData[provider]?.[model];
    if (!price) return 0; // 不明なモデルの場合は 0 を返す
    
    const inputCost = (tokenUsageInput / 1_000_000) * price.input;
    const outputCost = (tokenUsageOutput / 1_000_000) * price.output;
    return inputCost + outputCost;
  };

  // hasReloaded のデフォルト値を false に設定
  const [hasReloaded, setHasReloaded] = useState<boolean>(false);

  useEffect(() => {
    if (!shouldSubscribe || !isPolling) return;

    let cancelled = false;
    let retryCount = 0;
    const maxRetries = 10;

    async function poll() {
      if (cancelled) return;

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${slug}/status/step-json`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
            // キャッシュを防止するためのヘッダーを追加
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Pragma: "no-cache",
          },
        });

        if (response.ok) {
          const data = await response.json();

          if (data.token_usage !== undefined) {
            setTokenUsage(data.token_usage);
          }
          if (data.token_usage_input !== undefined) {
            setTokenUsageInput(data.token_usage_input);
          }
          if (data.token_usage_output !== undefined) {
            setTokenUsageOutput(data.token_usage_output);
          }
          if (data.estimated_cost !== undefined) {
            setEstimatedCost(data.estimated_cost);
          }
          if (data.provider !== undefined) {
            setProvider(data.provider);
          }
          if (data.model !== undefined) {
            setModel(data.model);
          }
          
          // トークン使用量が更新されたら、推定コストも計算して更新
          if (
            (data.token_usage_input !== undefined || data.token_usage_output !== undefined) &&
            data.provider !== undefined &&
            data.model !== undefined
          ) {
            const newTokenUsageInput = data.token_usage_input !== undefined ? data.token_usage_input : tokenUsageInput;
            const newTokenUsageOutput = data.token_usage_output !== undefined ? data.token_usage_output : tokenUsageOutput;
            const newEstimatedCost = calculateCost(
              data.provider,
              data.model,
              newTokenUsageInput,
              newTokenUsageOutput
            );
            setEstimatedCost(newEstimatedCost);
          }

          if (!data.current_step || data.current_step === "loading") {
            retryCount = 0;
            setTimeout(poll, 3000);
            return;
          }

          if (data.current_step === "error") {
            setErrorStep(data.error_step || lastValidStep);
            setProgress("error");
            setIsPolling(false);
            return;
          }

          setLastValidStep(data.current_step);
          setErrorStep(null);
          setProgress(data.current_step);

          if (data.current_step === "completed") {
            setIsPolling(false);
            return;
          }

          // 正常なレスポンスの場合は次のポーリングをスケジュール
          setTimeout(poll, 3000);
        } else {
          retryCount++;
          if (retryCount >= maxRetries) {
            console.error("Maximum retry attempts reached");
            setProgress("error");
            setIsPolling(false);
            return;
          }
          const retryInterval = retryCount < 3 ? 2000 : 5000;
          setTimeout(poll, retryInterval);
        }
      } catch (error) {
        console.error("Polling error:", error);
        retryCount++;
        if (retryCount >= maxRetries) {
          setProgress("error");
          setIsPolling(false);
          return;
        }
        setTimeout(poll, 5000);
      }
    }

    poll();

    return () => {
      cancelled = true;
    };
  }, [slug, shouldSubscribe, lastValidStep, isPolling]);

  useEffect(() => {
    // 完了またはエラーでかつリロード済みでない場合
    if ((progress === "completed" || progress === "error") && !hasReloaded) {
      setHasReloaded(true);

      const reloadTimeout = setTimeout(() => {
        window.location.reload();
      }, 1500);

      return () => clearTimeout(reloadTimeout);
    }
  }, [progress, hasReloaded]);

  return { progress, errorStep, tokenUsage, tokenUsageInput, tokenUsageOutput, estimatedCost, provider, model };
}

// 個々のレポートカードコンポーネント
function ReportCard({
  report,
  reports,
  setReports,
}: {
  report: Report;
  reports?: Report[];
  setReports?: (reports: Report[] | undefined) => void;
}) {
  const statusDisplay = getStatusDisplay(report.status);
  const { progress, errorStep, tokenUsage, tokenUsageInput, tokenUsageOutput, estimatedCost, provider, model } = useReportProgressPoll(
    report.slug,
    report.status !== "ready",
  );

  const currentStepIndex =
    progress === "completed" ? steps.length : stepKeys.indexOf(progress) === -1 ? 0 : stepKeys.indexOf(progress);

  const [lastProgress, setLastProgress] = useState<string | null>(null);
  const clusterDialogContentRef = useRef<HTMLDivElement>(null);

  // 編集ダイアログの状態管理
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editTitle, setEditTitle] = useState(report.title);
  const [editDescription, setEditDescription] = useState(report.description || "");

  // クラスタ編集ダイアログの状態管理
  const [isClusterEditDialogOpen, setIsClusterEditDialogOpen] = useState(false);
  const [clusters, setClusters] = useState<ClusterResponse[]>([]);
  const [selectedClusterId, setSelectedClusterId] = useState<string | undefined>(undefined);
  const [editClusterTitle, setEditClusterTitle] = useState("");
  const [editClusterDescription, setEditClusterDescription] = useState("");

  // エラー状態の判定
  const isErrorState = progress === "error" || report.status === "error";

  const displayTokenUsageInput = report.status === "processing" ? tokenUsageInput : report.tokenUsageInput;
  const displayTokenUsageOutput = report.status === "processing" ? tokenUsageOutput : report.tokenUsageOutput;
  const displayEstimatedCost = report.status === "processing" ? estimatedCost : report.estimatedCost;
  const displayTokenUsage = report.status === "processing" ? tokenUsage : report.tokenUsage;
  const displayProvider = report.status === "processing" ? provider : report.provider;
  const displayModel = report.status === "processing" ? model : report.model;

  // progress が変更されたときにレポート状態を更新
  useEffect(() => {
    if ((progress === "completed" || progress === "error") && progress !== lastProgress) {
      setLastProgress(progress);

      if (progress === "completed" && setReports) {
        const updatedReports = reports?.map((r) =>
          r.slug === report.slug
            ? {
                ...r,
                status: "ready",
                tokenUsage: tokenUsage || r.tokenUsage,
                tokenUsageInput: tokenUsageInput || r.tokenUsageInput,
                tokenUsageOutput: tokenUsageOutput || r.tokenUsageOutput,
                estimatedCost: estimatedCost || r.estimatedCost,
                provider: provider || r.provider,
                model: model || r.model,
              }
            : r,
        );
        setReports(updatedReports);
      } else if (progress === "error" && setReports) {
        const updatedReports = reports?.map((r) =>
          r.slug === report.slug
            ? {
                ...r,
                status: "error",
                tokenUsage: tokenUsage || r.tokenUsage,
                tokenUsageInput: tokenUsageInput || r.tokenUsageInput,
                tokenUsageOutput: tokenUsageOutput || r.tokenUsageOutput,
                estimatedCost: estimatedCost || r.estimatedCost,
                provider: provider || r.provider,
                model: model || r.model,
              }
            : r,
        );
        setReports(updatedReports);
      }
    }
  }, [progress, lastProgress, reports, setReports, report.slug, tokenUsage, tokenUsageInput, tokenUsageOutput, estimatedCost, provider, model]);
  return (
    <LinkBox
      as={Card.Root}
      key={report.slug}
      mb={4}
      borderLeftWidth={10}
      borderLeftColor={isErrorState ? "red.600" : statusDisplay.borderColor}
      position="relative"
      transition="all 0.2s"
      pointerEvents={isEditDialogOpen ? "none" : "auto"}
      _hover={
        report.status === "ready" && !isEditDialogOpen
          ? {
              backgroundColor: "gray.50",
              cursor: "pointer",
            }
          : {}
      }
      onClick={(e) => {
        if (report.status === "ready") {
          window.open(`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`, "_blank");
        }
        return true;
      }}
    >
      <Card.Body>
        <HStack justify="space-between">
          <HStack>
            <Box mr={3} color={isErrorState ? "red.600" : statusDisplay.iconColor}>
              {isErrorState ? <CircleAlertIcon size={30} /> : statusDisplay.icon}
            </Box>
            <Box>
              <LinkOverlay href={`/${report.slug}`} target="_blank" rel="noopener noreferrer">
                <Text fontSize="md" fontWeight="bold" color={isErrorState ? "red.600" : statusDisplay.textColor}>
                  {report.title}
                </Text>
              </LinkOverlay>
              <Card.Description>{`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}</Card.Description>
              {report.createdAt && (
                <Text fontSize="xs" color="gray.500" mb={1}>
                  作成日時:{" "}
                  {new Date(report.createdAt).toLocaleString("ja-JP", {
                    timeZone: "Asia/Tokyo",
                  })}
                </Text>
              )}
              {/* トークン使用量の表示を追加 */}
              <Text fontSize="xs" color="gray.500" mb={1}>
                トークン使用量:{" "}
                {report.status === "processing"
                  ? tokenUsageInput > 0 || tokenUsageOutput > 0
                    ? `入力: ${tokenUsageInput.toLocaleString()}, 出力: ${tokenUsageOutput.toLocaleString()}`
                    : tokenUsage > 0
                      ? `${tokenUsage.toLocaleString()} (詳細なし)`
                      : "情報なし"
                  : report.tokenUsageInput != null && report.tokenUsageOutput != null
                    ? `入力: ${report.tokenUsageInput.toLocaleString()}, 出力: ${report.tokenUsageOutput.toLocaleString()}`
                    : report.tokenUsage != null
                      ? `${report.tokenUsage.toLocaleString()} (詳細なし)`
                      : "情報なし"}
              </Text>
              {/* 推定コストの表示を追加 */}
              <Text fontSize="xs" color="gray.500" mb={1}>
                推定コスト:{" "}
                {report.status === "processing"
                  ? displayEstimatedCost != null && displayEstimatedCost > 0
                    ? `$${displayEstimatedCost.toFixed(6)}`
                    : "情報なし"
                  : report.estimatedCost != null
                    ? `$${report.estimatedCost.toFixed(6)}`
                    : "情報なし"}
                {displayProvider && displayModel ? ` (${displayProvider}/${displayModel})` : ""}
              </Text>
              {report.status !== "ready" && (
                <Box mt={2}>
                  <Steps.Root defaultStep={currentStepIndex} count={steps.length}>
                    <Steps.List>
                      {steps.map((step, index) => {
                        const isCompleted = index < currentStepIndex;

                        const stepColor = (() => {
                          if (progress === "error" && index === currentStepIndex) {
                            return "red.500";
                          }
                          if (isCompleted) return "green.500";
                          return "gray.300";
                        })();

                        return (
                          <Steps.Item key={step.id} index={index} title={step.title}>
                            <Flex direction="column" align="center">
                              <Steps.Indicator boxSize="24px" bg={stepColor} position="relative" />
                              <Steps.Title
                                mt={1}
                                fontSize="sm"
                                whiteSpace="nowrap"
                                textAlign="center"
                                color={stepColor}
                                fontWeight={progress === "error" && index === currentStepIndex ? "bold" : "normal"}
                              >
                                {step.title}
                              </Steps.Title>
                            </Flex>
                            <Steps.Separator borderColor={stepColor} />
                          </Steps.Item>
                        );
                      })}
                    </Steps.List>
                  </Steps.Root>
                </Box>
              )}
            </Box>
          </HStack>
          {report.status === "ready" && (
            <Box
              position="absolute"
              top="0"
              left="0"
              right="0"
              bottom="0"
              display="flex"
              alignItems="center"
              justifyContent="center"
              backgroundColor="blackAlpha.100"
              opacity="0"
              transition="opacity 0.2s"
              _hover={{ opacity: 1 }}
              pointerEvents="auto"
              zIndex="10"
            >
              <Button variant="solid" size="sm" bg="white" color="black" zIndex="50" pointerEvents="auto">
                <Flex align="center" gap={2}>
                  <ExternalLinkIcon size={16} />
                  <Text>レポートを見る</Text>
                </Flex>
              </Button>
            </Box>
          )}
          <HStack position="relative" zIndex="20">
            {report.status === "ready" && report.isPubcom && (
              <Popover.Root>
                <Popover.Trigger asChild>
                  <Button
                    variant="ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                  >
                    <Tooltip content="CSVファイルをダウンロード" openDelay={0} closeDelay={0}>
                      <Icon>
                        <DownloadIcon />
                      </Icon>
                    </Tooltip>
                  </Button>
                </Popover.Trigger>
                <Portal>
                  <Popover.Positioner>
                    <Popover.Content>
                      <Popover.Arrow />
                      <Popover.Body p={0}>
                        <VStack align="stretch" gap={0}>
                          <Button
                            variant="ghost"
                            justifyContent="flex-start"
                            borderRadius={0}
                            py={2}
                            onClick={async (e) => {
                              e.stopPropagation();
                              try {
                                const response = await fetch(`${getApiBaseUrl()}/admin/comments/${report.slug}/csv`, {
                                  headers: {
                                    "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                                    "Content-Type": "application/json",
                                  },
                                });
                                if (!response.ok) {
                                  const errorData = await response.json();
                                  throw new Error(errorData.detail || "CSV ダウンロードに失敗しました");
                                }
                                const blob = await response.blob();
                                const url = window.URL.createObjectURL(blob);
                                const link = document.createElement("a");
                                link.href = url;
                                link.download = `kouchou_${report.slug}.csv`;
                                link.click();
                                window.URL.revokeObjectURL(url);
                              } catch (error) {
                                console.error(error);
                              }
                            }}
                          >
                            CSV
                          </Button>
                          <Button
                            variant="ghost"
                            justifyContent="flex-start"
                            borderRadius={0}
                            py={2}
                            onClick={async (e) => {
                              e.stopPropagation();
                              try {
                                const response = await fetch(`${getApiBaseUrl()}/admin/comments/${report.slug}/csv`, {
                                  headers: {
                                    "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                                    "Content-Type": "application/json",
                                  },
                                });
                                if (!response.ok) {
                                  const errorData = await response.json();
                                  throw new Error(errorData.detail || "CSV ダウンロードに失敗しました");
                                }
                                const blob = await response.blob();
                                const text = await blob.text();
                                // UTF-8 BOMを追加
                                const bom = "\uFEFF";
                                const bomBlob = new Blob([bom + text], {
                                  type: "text/csv;charset=utf-8",
                                });
                                const url = window.URL.createObjectURL(bomBlob);
                                const link = document.createElement("a");
                                link.href = url;
                                link.download = `kouchou_${report.slug}_excel.csv`;
                                link.click();
                                window.URL.revokeObjectURL(url);
                              } catch (error) {
                                console.error(error);
                              }
                            }}
                          >
                            CSV for Excel(Windows)
                          </Button>
                        </VStack>
                      </Popover.Body>
                    </Popover.Content>
                  </Popover.Positioner>
                </Portal>
              </Popover.Root>
            )}
            {report.status === "ready" && (
              <Box
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
              >
                {(() => {
                  const visibilityOptions = createListCollection({
                    items: [
                      { label: "公開", value: "public" },
                      { label: "限定公開", value: "unlisted" },
                      { label: "非公開", value: "private" },
                    ],
                  });

                  return (
                    <Select.Root
                      collection={visibilityOptions}
                      size="sm"
                      width="150px"
                      defaultValue={[report.visibility.toString()]}
                      onValueChange={async (value) => {
                        // valueは配列の可能性があるため、最初の要素を取得
                        const selected = Array.isArray(value?.value) ? value?.value[0] : value?.value;
                        if (!selected || selected === report.visibility.toString()) return;
                        try {
                          const response = await fetch(`${getApiBaseUrl()}/admin/reports/${report.slug}/visibility`, {
                            method: "PATCH",
                            headers: {
                              "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                              "Content-Type": "application/json",
                            },
                            body: JSON.stringify({ visibility: selected }),
                          });
                          if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || "公開状態の変更に失敗しました");
                          }
                          const data = await response.json();
                          const updatedReports = reports?.map((r) =>
                            r.slug === report.slug ? { ...r, visibility: data.visibility } : r,
                          );
                          if (setReports) {
                            setReports(updatedReports);
                          }
                        } catch (error) {
                          console.error(error);
                        }
                      }}
                    >
                      <Select.HiddenSelect />
                      <Select.Control>
                        <Select.Trigger>
                          <Select.ValueText placeholder="公開状態" />
                        </Select.Trigger>
                        <Select.IndicatorGroup>
                          <Select.Indicator />
                        </Select.IndicatorGroup>
                      </Select.Control>
                      <Portal>
                        <Select.Positioner>
                          <Select.Content>
                            {visibilityOptions.items.map((option) => (
                              <Select.Item item={option} key={option.value}>
                                {option.label}
                                <Select.ItemIndicator />
                              </Select.Item>
                            ))}
                          </Select.Content>
                        </Select.Positioner>
                      </Portal>
                    </Select.Root>
                  );
                })()}
              </Box>
            )}
            <MenuRoot>
              <MenuTrigger asChild>
                <Button variant="ghost" size="lg" onClick={(e) => e.stopPropagation()}>
                  <EllipsisIcon />
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem value="duplicate">レポートを複製して新規作成(開発中)</MenuItem>
                <MenuItem
                  value="edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditTitle(report.title);
                    setEditDescription(report.description || "");
                    setIsEditDialogOpen(true);
                  }}
                >
                  レポートを編集する
                </MenuItem>
                {report.status === "ready" && (
                  <MenuItem
                    value="edit-cluster"
                    onClick={async (e) => {
                      e.stopPropagation();
                      try {
                        const response = await fetch(`${getApiBaseUrl()}/admin/reports/${report.slug}/cluster-labels`, {
                          headers: {
                            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                          },
                        });
                        if (!response.ok) {
                          throw new Error("クラスタ一覧の取得に失敗しました");
                        }
                        const data = await response.json();
                        setClusters(data.clusters || []);
                        if (data.clusters && data.clusters.length > 0) {
                          setSelectedClusterId(data.clusters[0].id);
                          setEditClusterTitle(data.clusters[0].label);
                          setEditClusterDescription(data.clusters[0].description);
                        } else {
                          setSelectedClusterId(undefined);
                          setEditClusterTitle("");
                          setEditClusterDescription("");
                        }
                        setIsClusterEditDialogOpen(true);
                      } catch (error) {
                        console.error(error);
                        toaster.create({
                          type: "error",
                          title: "エラー",
                          description: "クラスタ一覧の取得に失敗しました。",
                        });
                      }
                    }}
                  >
                    意見グループを編集する
                  </MenuItem>
                )}
                <MenuItem
                  value="delete"
                  color="fg.error"
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (confirm(`レポート「${report.title}」を削除してもよろしいですか？`)) {
                      try {
                        const response = await fetch(
                          `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${report.slug}`,
                          {
                            method: "DELETE",
                            headers: {
                              "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                              "Content-Type": "application/json",
                            },
                          },
                        );
                        if (response.ok) {
                          alert("レポートを削除しました");
                          window.location.reload();
                        } else {
                          const errorData = await response.json();
                          throw new Error(errorData.detail || "レポートの削除に失敗しました");
                        }
                      } catch (error) {
                        console.error(error);
                      }
                    }
                  }}
                >
                  レポートを削除する
                </MenuItem>
              </MenuContent>
            </MenuRoot>
          </HStack>
        </HStack>
      </Card.Body>

      <Dialog.Root
        open={isEditDialogOpen}
        onOpenChange={({ open }) => setIsEditDialogOpen(open)}
        modal={true}
        closeOnInteractOutside={true}
        trapFocus={true}
      >
        <Portal>
          <Dialog.Backdrop
            zIndex={1000}
            position="fixed"
            inset={0}
            backgroundColor="blackAlpha.100"
            backdropFilter="blur(2px)"
          />
          <Dialog.Positioner>
            <Dialog.Content
              pointerEvents="auto"
              position="relative"
              zIndex={1001}
              boxShadow="md"
              onClick={(e) => e.stopPropagation()}
            >
              <Dialog.CloseTrigger position="absolute" top={3} right={3} />
              <Dialog.Header>
                <Dialog.Title>レポートを編集</Dialog.Title>
              </Dialog.Header>
              <Dialog.Body>
                <VStack gap={4} align="stretch">
                  <Box>
                    <Text mb={2} fontWeight="bold">
                      タイトル
                    </Text>
                    <Input
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      placeholder="レポートのタイトルを入力"
                    />
                  </Box>
                  <Box>
                    <Text mb={2} fontWeight="bold">
                      調査概要
                    </Text>
                    <Textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      placeholder="調査の概要を入力"
                    />
                  </Box>
                </VStack>
              </Dialog.Body>
              <Dialog.Footer>
                <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                  キャンセル
                </Button>
                <Button
                  ml={3}
                  onClick={async () => {
                    try {
                      const response = await fetch(`${getApiBaseUrl()}/admin/reports/${report.slug}/config`, {
                        method: "PATCH",
                        headers: {
                          "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                          "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                          question: editTitle,
                          intro: editDescription,
                        }),
                      });

                      if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || "メタデータの更新に失敗しました");
                      }

                      // レポート一覧を更新
                      if (setReports && reports) {
                        const updatedReports = reports.map((r) =>
                          r.slug === report.slug
                            ? {
                                ...r,
                                title: editTitle,
                                description: editDescription,
                              }
                            : r,
                        );
                        setReports(updatedReports);
                      }

                      // 成功メッセージを表示
                      toaster.create({
                        type: "success",
                        title: "更新完了",
                        description: "レポート情報が更新されました",
                      });

                      // ダイアログを閉じる
                      setIsEditDialogOpen(false);
                    } catch (error) {
                      console.error("メタデータの更新に失敗しました:", error);
                      toaster.create({
                        type: "error",
                        title: "更新エラー",
                        description: "メタデータの更新に失敗しました",
                      });
                    }
                  }}
                >
                  保存
                </Button>
              </Dialog.Footer>
            </Dialog.Content>
          </Dialog.Positioner>
        </Portal>
      </Dialog.Root>

      {/* クラスタ編集ダイアログ */}
      <ClusterEditDialog
        report={report}
        isOpen={isClusterEditDialogOpen}
        onClose={() => setIsClusterEditDialogOpen(false)}
        clusters={clusters}
        setClusters={setClusters}
        selectedClusterId={selectedClusterId}
        setSelectedClusterId={setSelectedClusterId}
        editClusterTitle={editClusterTitle}
        setEditClusterTitle={setEditClusterTitle}
        editClusterDescription={editClusterDescription}
        setEditClusterDescription={setEditClusterDescription}
      />
    </LinkBox>
  );
}

function DownloadBuildButton() {
  const [isLoading, setIsLoading] = useState(false);

  const handleDownload = async () => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/download");

      if (!res.ok) {
        throw new Error("ビルドに失敗しました");
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("Content-Disposition");
      const match = contentDisposition?.match(/filename="?(.+)"?/);
      const filename = match?.[1] ?? "kouchou-ai.zip";

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      toaster.create({
        type: "success",
        duration: 5000,
        title: "エクスポート完了",
        description: "ダウンロードフォルダに保存されました。",
      });
    } catch (error) {
      toaster.create({
        type: "error",
        duration: 5000,
        title: "エクスポート失敗",
        description: "問題が解決しない場合は、管理者に問い合わせてください。",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Button size="xl" onClick={handleDownload} loading={isLoading} loadingText="エクスポート中">
      全レポートをエクスポート
    </Button>
  );
}

const EmptyState = () => {
  return (
    <VStack mt={8} gap={0} lineHeight={2}>
      <Text fontSize="18px" fontWeight="bold">
        レポートが0件です
      </Text>
      <Text fontSize="14px" textAlign={{ md: "center" }} mt={5}>
        レポートが作成されるとここに一覧が表示され、
        <Box as="br" display={{ base: "none", md: "block" }} />
        公開やダウンロードなどの操作が行えるようになります。
      </Text>
      <Text fontSize="12px" color="gray.500" mt={3}>
        レポート作成が開始済みの場合は、AI分析が完了するまでしばらくお待ちください。
      </Text>
      <Image src="images/report-empty.png" mt={8} />
      <Box mt={8}>
        <Link href="/create">
          <Button size="xl">新しいレポートを作成する</Button>
        </Link>
      </Box>
    </VStack>
  );
};

export default function Page() {
  const [reports, setReports] = useState<Report[]>();

  useEffect(() => {
    (async () => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports`, {
        method: "GET",
        headers: {
          "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
          "Content-Type": "application/json",
        },
      });
      if (!response.ok) return;
      setReports(await response.json());
    })();
  }, []);

  return (
    <div className="container">
      <Header />
      <Box mx="auto" maxW="1000px">
        <Heading textAlign="left" fontSize="xl" mb={8}>
          レポート一覧
        </Heading>
        {!reports && (
          <VStack>
            <Spinner />
          </VStack>
        )}
        {reports && reports.length === 0 && <EmptyState />}
        {reports && reports.length > 0 && (
          <>
            {reports.map((report) => (
              <ReportCard key={report.slug} report={report} reports={reports} setReports={setReports} />
            ))}
            <HStack justify="center" mt={10}>
              <Link href="/create">
                <Button size="xl">新しいレポートを作成する</Button>
              </Link>
              <DownloadBuildButton />
              <Link href="/environment">
                <Button size="xl" variant="outline">
                  環境検証
                </Button>
              </Link>
            </HStack>
          </>
        )}
      </Box>
    </div>
  );
}
