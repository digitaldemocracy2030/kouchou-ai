"use client";

import { getApiBaseUrl } from "@/app/utils/api";
import type { Report } from "@/type";
import { Box, Field, HStack, NativeSelect, Spinner, Text, VStack } from "@chakra-ui/react";
import { useEffect, useState } from "react";

interface ReportConfig {
  question?: string;
  intro?: string;
  cluster?: number[];
  model?: string;
  provider?: string;
  workers?: number;
  is_pubcom?: boolean;
  is_embedded_at_local?: boolean;
  local_llm_address?: string;
  prompt?: {
    extraction?: string;
    initial_labelling?: string;
    merge_labelling?: string;
    overview?: string;
  };
}

interface ExistingReportTabProps {
  selectedReportSlug: string;
  setSelectedReportSlug: (slug: string) => void;
  onReportConfigLoaded: (config: ReportConfig) => void;
}

export function ExistingReportTab({
  selectedReportSlug,
  setSelectedReportSlug,
  onReportConfigLoaded,
}: ExistingReportTabProps) {
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [configLoading, setConfigLoading] = useState(false);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/admin/reports`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
          },
        });
        if (response.ok) {
          const reportsData = await response.json();
          // 完成済みのレポートのみフィルタ
          const readyReports = reportsData.filter((report: Report) => report.status === "ready");
          setReports(readyReports);
        }
      } catch (error) {
        console.error("Failed to fetch reports:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchReports();
  }, []);

  const handleReportSelection = async (slug: string) => {
    setSelectedReportSlug(slug);

    if (slug && slug !== "") {
      setConfigLoading(true);
      try {
        const response = await fetch(`${getApiBaseUrl()}/admin/reports/${slug}/config`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const config = await response.json();
          onReportConfigLoaded(config);
        } else {
          console.error("Failed to fetch report config:", response.statusText);
        }
      } catch (error) {
        console.error("Failed to fetch report config:", error);
      } finally {
        setConfigLoading(false);
      }
    }
  };

  if (loading) {
    return (
      <VStack py={8}>
        <Spinner />
        <Text>レポート一覧を読み込み中...</Text>
      </VStack>
    );
  }

  if (reports.length === 0) {
    return (
      <VStack py={8}>
        <Text fontSize="lg" fontWeight="bold">
          利用可能なレポートがありません
        </Text>
        <Text fontSize="sm" color="gray.500">
          完成済みのレポートがある場合のみ、この機能を利用できます。
        </Text>
      </VStack>
    );
  }

  return (
    <VStack align="stretch" gap={6}>
      <Field.Root>
        <Field.Label>再利用するレポート *</Field.Label>
        <NativeSelect.Root disabled={configLoading}>
          <NativeSelect.Field
            value={selectedReportSlug}
            onChange={(e) => handleReportSelection(e.target.value)}
            placeholder="レポートを選択してください"
          >
            <option value="">レポートを選択してください</option>
            {reports.map((report) => (
              <option key={report.slug} value={report.slug}>
                {report.title} ({report.slug})
              </option>
            ))}
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        {configLoading && (
          <HStack gap={2} mt={2}>
            <Spinner size="sm" />
            <Text fontSize="sm" color="gray.600">
              設定を読み込み中...
            </Text>
          </HStack>
        )}
      </Field.Root>

      {selectedReportSlug && (
        <Box p={4} bg="blue.50" borderRadius="md" borderLeft="4px solid" borderLeftColor="blue.500">
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            ✅ 複製元レポートが選択されました
          </Text>
          <Text fontSize="xs" color="gray.600">
            レポート作成時に、変更されたパラメータに応じて必要なステップから自動的に実行されます。
          </Text>
        </Box>
      )}
    </VStack>
  );
}
