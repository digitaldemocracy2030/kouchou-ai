"use client";

import { getApiBaseUrl } from "@/app/utils/api";
import { Header } from "@/components/Header";
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu";
import { toaster } from "@/components/ui/toaster";
import { Tooltip } from "@/components/ui/tooltip";
import type { Report } from "@/type";
import {
  Box,
  Button,
  Card,
  Dialog,
  Flex,
  HStack,
  Heading,
  Icon,
  Input,
  Popover,
  Portal,
  Spinner,
  Steps,
  Text,
  Textarea,
  VStack
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
import { useEffect, useState } from "react";

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
  { id: 3, title: "クラスタリング", description: "階層的クラスタリングの実施" },
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
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${slug}/status/step-json`,
          {
            headers: {
              "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
              "Content-Type": "application/json",
              // キャッシュを防止するためのヘッダーを追加
              "Cache-Control": "no-cache, no-store, must-revalidate",
              "Pragma": "no-cache"
            },
          },
        );

        if (response.ok) {
          const data = await response.json();

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

  return { progress, errorStep };
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
  const { progress, errorStep } = useReportProgressPoll(
    report.slug,
    report.status !== "ready",
  );

  const currentStepIndex =
    progress === "completed"
      ? steps.length
      : stepKeys.indexOf(progress) === -1
        ? 0
        : stepKeys.indexOf(progress);

  const [lastProgress, setLastProgress] = useState<string | null>(null);
  
  // 編集ダイアログの状態管理
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editTitle, setEditTitle] = useState(report.title);
  const [editDescription, setEditDescription] = useState(report.description || "");

  // エラー状態の判定
  const isErrorState = progress === "error" || report.status === "error";

  // progress が変更されたときにレポート状態を更新
  useEffect(() => {
    if ((progress === "completed" || progress === "error") && progress !== lastProgress) {
      setLastProgress(progress);

      if (progress === "completed" && setReports) {
        const updatedReports = reports?.map((r) =>
          r.slug === report.slug ? { ...r, status: "ready" } : r
        );
        setReports(updatedReports);
      } else if (progress === "error" && setReports) {
        const updatedReports = reports?.map((r) =>
          r.slug === report.slug ? { ...r, status: "error" } : r
        );
        setReports(updatedReports);
      }
    }
  }, [progress, lastProgress, reports, setReports, report.slug]);
  return (
    <Card.Root
      size="md"
      key={report.slug}
      mb={4}
      borderLeftWidth={10}
      borderLeftColor={isErrorState ? "red.600" : statusDisplay.borderColor}
      position="relative"
      transition="all 0.2s"
      role="group"
      pointerEvents={isEditDialogOpen ? "none" : "auto"}
      _hover={report.status === "ready" && !isEditDialogOpen ? {
        backgroundColor: "gray.50",
        cursor: "pointer",
      } : {}}
      onClick={(e) => {
        // ダイアログが開いている場合は何もしない
        if (isEditDialogOpen) {
          e.preventDefault();
          e.stopPropagation();
          return false;
        }
        
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
              {isErrorState ? (
                <CircleAlertIcon size={30} />
              ) : (
                statusDisplay.icon
              )}
            </Box>
            <Box>
              <Card.Title>
                <Text fontSize="md" color={isErrorState ? "red.600" : statusDisplay.textColor}>
                  {report.title}
                </Text>
              </Card.Title>
              <Card.Description>
                {`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}
              </Card.Description>
              {report.createdAt && (
                <Text fontSize="xs" color="gray.500" mb={1}>
                  作成日時:{" "}
                  {new Date(report.createdAt).toLocaleString(
                    "ja-JP",
                    { timeZone: "Asia/Tokyo" },
                  )}
                </Text>
              )}
              {report.status !== "ready" && (
                <Box mt={2}>
                  <Steps.Root
                    defaultStep={currentStepIndex}
                    count={steps.length}
                  >
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
                          <Steps.Item
                            key={step.id}
                            index={index}
                            title={step.title}
                          >
                            <Flex direction="column" align="center">
                              <Steps.Indicator
                                boxSize="24px"
                                bg={stepColor}
                                position="relative"
                              />
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
                            <Steps.Separator
                              borderColor={stepColor}
                            />
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
              backgroundColor="rgba(0, 0, 0, 0.05)"
              opacity="0"
              transition="opacity 0.2s"
              _hover={{ opacity: 1 }}
              pointerEvents="auto"
              zIndex="10"
            >
              <Button
                variant="solid"
                size="sm"
                bg="white"
                color="black"
                zIndex="50"
                pointerEvents="auto"
              >
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
                      <Tooltip
                        content="CSVファイルをダウンロード"
                        openDelay={0}
                        closeDelay={0}
                      >
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
                                const response = await fetch(
                                  `${getApiBaseUrl()}/admin/comments/${report.slug}/csv`,
                                  {
                                    headers: {
                                      "x-api-key":
                                        process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                                      "Content-Type": "application/json",
                                    },
                                  },
                                );
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
                                const response = await fetch(
                                  `${getApiBaseUrl()}/admin/comments/${report.slug}/csv`,
                                  {
                                    headers: {
                                      "x-api-key":
                                        process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                                      "Content-Type": "application/json",
                                    },
                                  },
                                );
                                if (!response.ok) {
                                  const errorData = await response.json();
                                  throw new Error(errorData.detail || "CSV ダウンロードに失敗しました");
                                }
                                const blob = await response.blob();
                                const text = await blob.text();
                                // UTF-8 BOMを追加
                                const bom = "\uFEFF";
                                const bomBlob = new Blob([bom + text], { type: "text/csv;charset=utf-8" });
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
              <>
                <Tooltip
                  content={report.isPublic ? "公開中" : "非公開"}
                  openDelay={0}
                  closeDelay={0}
                >
                  <Box display="flex" alignItems="center">
                    <Button
                      variant={report.isPublic ? "solid" : "outline"}
                      size="sm"
                      onClick={async (e) => {
                        e.stopPropagation();
                        try {
                          const response = await fetch(
                            `${getApiBaseUrl()}/admin/reports/${report.slug}/visibility`,
                            {
                              method: "PATCH",
                              headers: {
                                "x-api-key":
                                  process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                                "Content-Type": "application/json",
                              },
                            },
                          );
                          if (!response.ok) {
                            const errorData = await response.json();
                            throw new Error(errorData.detail || "公開状態の変更に失敗しました");
                          }
                          const data = await response.json();
                          const updatedReports = reports?.map((r) =>
                            r.slug === report.slug
                              ? { ...r, isPublic: data.isPublic }
                              : r,
                          );
                          if (setReports) {
                            setReports(updatedReports);
                          }
                        } catch (error) {
                          console.error(error);
                        }
                      }}
                    >
                      {report.isPublic ? "公開中" : "非公開"}
                    </Button>
                  </Box>
                </Tooltip>
              </>
            )}
            <MenuRoot>
              <MenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="lg"
                  onClick={(e) => e.stopPropagation()}
                >
                  <EllipsisIcon />
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem value="duplicate">
                  レポートを複製して新規作成(開発中)
                </MenuItem>
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
                <MenuItem
                  value="delete"
                  color="fg.error"
                  onClick={async (e) => {
                    e.stopPropagation();
                    if (
                      confirm(
                        `レポート「${report.title}」を削除してもよろしいですか？`,
                      )
                    ) {
                      try {
                        const response = await fetch(
                          `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${report.slug}`,
                          {
                            method: "DELETE",
                            headers: {
                              "x-api-key":
                                process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
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
        closeOnInteractOutside={false}
        trapFocus={true}
      >
        <Dialog.Backdrop
          style={{
            zIndex: 1000,
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0, 0, 0, 0.4)",
            backdropFilter: "blur(2px)"
          }}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
          }}
        />
        <Dialog.Positioner>
          <Dialog.Content
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              return false;
            }}
            style={{
              pointerEvents: "auto",
              position: "relative",
              zIndex: 1001,
              boxShadow: "0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08)"
            }}
          >
            <Dialog.CloseTrigger position="absolute" top={3} right={3} />
            <Dialog.Header>
              <Dialog.Title>レポートを編集</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <VStack gap={4} align="stretch">
                <Box>
                  <Text mb={2} fontWeight="bold">タイトル</Text>
                  <Input
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    placeholder="レポートのタイトルを入力"
                  />
                </Box>
                <Box>
                  <Text mb={2} fontWeight="bold">調査概要</Text>
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
                    const response = await fetch(
                      `${getApiBaseUrl()}/admin/reports/${report.slug}/metadata`,
                      {
                        method: "PATCH",
                        headers: {
                          "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
                          "Content-Type": "application/json",
                        },
                        body: JSON.stringify({
                          title: editTitle,
                          description: editDescription,
                        }),
                      }
                    );

                    if (!response.ok) {
                      const errorData = await response.json();
                      throw new Error(errorData.detail || "メタデータの更新に失敗しました");
                    }

                    // レポート一覧を更新
                    if (setReports && reports) {
                      const updatedReports = reports.map((r) =>
                        r.slug === report.slug
                          ? { ...r, title: editTitle, description: editDescription }
                          : r
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
      </Dialog.Root>
    </Card.Root>
  );
}

export default function Page() {
  const [reports, setReports] = useState<Report[]>();

  useEffect(() => {
    (async () => {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports`,
        {
          method: "GET",
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
          },
        },
      );
      if (!response.ok) return;
      setReports(await response.json());
    })();
  }, []);

  return (
    <div className="container">
      <Header />
      <Box mx="auto" maxW="1000px" mb={5}>
        <Heading textAlign="center" fontSize="xl" mb={5}>
          Admin Dashboard
        </Heading>
        <Heading textAlign="center" fontSize="xl" mb={5}>
          Reports
        </Heading>
        {!reports && (
          <VStack>
            <Spinner />
          </VStack>
        )}
        {reports && reports.length === 0 && (
          <VStack my={10}>
            <Text>レポートがありません</Text>
          </VStack>
        )}
        {reports &&
          reports.length > 0 &&
          reports.map((report) => (
            <ReportCard
              key={report.slug}
              report={report}
              reports={reports}
              setReports={setReports}
            />
          ))}
        <HStack justify="center" mt={10}>
          <Link href="/create">
            <Button size="xl">新しいレポートを作成する</Button>
          </Link>
        </HStack>
      </Box>
    </div>
  );
}
