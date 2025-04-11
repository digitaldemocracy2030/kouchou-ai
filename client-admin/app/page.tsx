"use client";

import { getApiBaseUrl } from "@/app/utils/api";
import { Header } from "@/components/Header";
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "@/components/ui/menu";
import { Tooltip } from "@/components/ui/tooltip";
import type { Report } from "@/type";
import {
  Box,
  Button,
  Card,
  Flex,
  HStack,
  Heading,
  Icon,
  Spinner,
  Steps,
  Text,
  VStack,
} from "@chakra-ui/react";
import {
  CircleAlertIcon,
  CircleCheckIcon,
  CircleFadingArrowUpIcon,
  DownloadIcon,
  EllipsisIcon,
  ExternalLinkIcon,
  FileDownIcon,
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
          <HStack>
            {report.status === "ready" && report.isPubcom && (
              <Tooltip
                content="CSVファイルをダウンロード"
                openDelay={0}
                closeDelay={0}
              >
                <Button
                  variant="ghost"
                  onClick={async () => {
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
                  <Icon>
                    <DownloadIcon />
                  </Icon>
                </Button>
              </Tooltip>
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
                      onClick={async () => {
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
                <Link
                  href={`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}
                  target="_blank"
                >
                  <Button variant="ghost">
                    <ExternalLinkIcon />
                  </Button>
                </Link>
              </>
            )}
            <MenuRoot>
              <MenuTrigger asChild>
                <Button variant="ghost" size="lg">
                  <EllipsisIcon />
                </Button>
              </MenuTrigger>
              <MenuContent>
                <MenuItem value="duplicate">
                  レポートを複製して新規作成(開発中)
                </MenuItem>
                <MenuItem
                  value="delete"
                  color="fg.error"
                  onClick={async () => {
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
        <HStack justify="center" mb={5}>
          <Tooltip
            content="静的HTMLをエクスポート"
            openDelay={0}
            closeDelay={0}
          >
            <Button
              colorScheme="blue"
              variant="outline"
              onClick={async () => {
                try {
                  alert("静的HTMLのエクスポートを開始します。このプロセスには数分かかることがあります。");
                  
                  const response = await fetch(
                    `${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/api/static-export`,
                    {
                      method: "GET",
                      headers: {
                        "Content-Type": "application/json",
                      },
                    },
                  );
                  if (!response.ok) {
                    throw new Error("静的エクスポート失敗");
                  }
                  
                  const blob = await response.blob();
                  const url = window.URL.createObjectURL(blob);
                  const link = document.createElement("a");
                  link.href = url;
                  link.download = "static_export.zip";
                  link.click();
                  window.URL.revokeObjectURL(url);
                  
                  alert("静的HTMLのエクスポートが完了しました");
                } catch (error) {
                  console.error(error);
                  alert("静的HTMLのエクスポートに失敗しました");
                }
              }}
            >
              <Icon>
                <FileDownIcon />
              </Icon>
              全レポートをエクスポート
            </Button>
          </Tooltip>
        </HStack>
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
