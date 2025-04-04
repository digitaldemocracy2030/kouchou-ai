'use client'

import { Header } from '@/components/Header'
import { Report } from '@/type'
import {
  Box,
  Button,
  Card,
  Flex,
  Heading,
  HStack,
  Spinner,
  Text,
  VStack,
  Icon,
  Steps
} from '@chakra-ui/react'
import Link from 'next/link'
import {
  CircleCheckIcon,
  CircleFadingArrowUpIcon,
  CircleAlertIcon,
  EllipsisIcon,
  ExternalLinkIcon,
  DownloadIcon
} from 'lucide-react'
import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from '@/components/ui/menu'
import { Tooltip } from '@/components/ui/tooltip'
import { getApiBaseUrl } from '@/app/utils/api'
import { useEffect, useState } from 'react'

// ステップの定義
const stepKeys = [
  'extraction',
  'embedding',
  'hierarchical_clustering',
  'hierarchical_initial_labelling',
  'hierarchical_merge_labelling',
  'hierarchical_overview',
  'hierarchical_aggregation',
  'hierarchical_visualization'
]

const steps = [
  { title: '抽出', description: 'データの抽出' },
  { title: '埋め込み', description: '埋め込み表現の生成' },
  { title: 'クラスタリング', description: '階層的クラスタリングの実施' },
  { title: '初期ラベリング', description: '初期ラベルの付与' },
  { title: '統合ラベリング', description: 'ラベルの統合' },
  { title: '概要生成', description: '概要の作成' },
  { title: '集約', description: '結果の集約' },
  { title: '可視化', description: '結果の可視化' }
]

// ステータスに応じた表示内容を返す関数
function getStatusDisplay(status: string) {
  switch (status) {
    case 'ready':
      return {
        borderColor: 'green',
        iconColor: 'green',
        textColor: '#2577b1',
        icon: <CircleCheckIcon size={30} />
      }
    case 'error':
      return {
        borderColor: 'red.600',
        iconColor: 'red.600',
        textColor: 'red.600',
        icon: <CircleAlertIcon size={30} />
      }
    default:
      return {
        borderColor: 'gray',
        iconColor: 'gray',
        textColor: 'gray',
        icon: <CircleFadingArrowUpIcon size={30} />
      }
  }
}

// カスタムフック：fetchを用いて指定レポートの進捗を定期ポーリングで取得
function useReportProgressPoll(slug: string, shouldSubscribe: boolean) {
  const [progress, setProgress] = useState<string>('loading')

  useEffect(() => {
    if (!shouldSubscribe) return

    let cancelled = false

    async function poll() {
      try {
        const response = await fetch(
          process.env.NEXT_PUBLIC_API_BASEPATH +
          `/admin/reports/${slug}/status/step-json`,
          {
            headers: {
              'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
              'Content-Type': 'application/json'
            }
          }
        )
        if (response.ok) {
          const data = await response.json()
          setProgress(data.current_step)
          // もし 'completed' ならポーリングを終了する（以降更新しない）
          if (data.current_step === 'completed') return
        } else {
          setProgress('error')
        }
      } catch (_error) {
        setProgress('error')
      }
      if (!cancelled) {
        setTimeout(poll, 5000)
      }
    }
    poll()

    return () => {
      cancelled = true
    }
  }, [slug, shouldSubscribe])

  return progress
}

// 個々のレポートカードコンポーネント
function ReportCard({ report }: { report: Report }) {
  const statusDisplay = getStatusDisplay(report.status)
  // report.status が 'ready' でない場合はポーリングを有効にする
  const progress = useReportProgressPoll(report.slug, report.status !== 'ready')
  // progress が 'completed' なら、currentStepIndex を全ステップ完了として設定
  const currentStepIndex =
    progress === 'completed'
      ? steps.length
      : stepKeys.indexOf(progress) === -1
        ? 0
        : stepKeys.indexOf(progress)

  // progress が 'completed' になったらページを1秒後にリロード
  useEffect(() => {
    if (progress === 'completed') {
      setTimeout(() => window.location.reload(), 1000)
    }
  }, [progress])

  return (
    <Card.Root
      size="md"
      key={report.slug}
      mb={4}
      borderLeftWidth={10}
      borderLeftColor={statusDisplay.borderColor}
    >
      <Card.Body>
        <HStack justify="space-between">
          <HStack>
            <Box mr={3} color={statusDisplay.iconColor}>
              {statusDisplay.icon}
            </Box>
            <Box>
              <Card.Title>
                <Text fontSize="md" color={statusDisplay.textColor}>
                  {report.title}
                </Text>
              </Card.Title>
              <Card.Description>
                {`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`}
              </Card.Description>
              {report.status !== 'ready' && (
                <Box mt={2}>
                  <Steps.Root defaultStep={currentStepIndex} count={steps.length}>
                    <Steps.List>
                      {steps.map((step, index) => {
                        const isCompleted = index < currentStepIndex
                        return (
                          <Steps.Item key={index} index={index} title={step.title}>
                            <Flex direction="column" align="center">
                              <Steps.Indicator
                                boxSize="24px"
                                bg={isCompleted ? 'green.500' : 'gray.300'}
                              />
                              <Steps.Title
                                mt={1}
                                fontSize="sm"
                                whiteSpace="nowrap"
                                textAlign="center"
                                color={isCompleted ? 'green.500' : 'gray.300'}
                              >
                                {step.title}
                              </Steps.Title>
                            </Flex>
                            <Steps.Separator borderColor={isCompleted ? 'green.500' : 'gray.300'} />
                          </Steps.Item>
                        )
                      })}
                    </Steps.List>
                  </Steps.Root>
                </Box>
              )}
            </Box>
          </HStack>
          <HStack>
            {report.status === 'ready' && report.isPubcom && (
              <Tooltip content="CSVファイルをダウンロード" openDelay={0} closeDelay={0}>
                <Button
                  variant="ghost"
                  onClick={async () => {
                    try {
                      const response = await fetch(getApiBaseUrl() + `/admin/comments/${report.slug}/csv`, {
                        headers: {
                          'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
                          'Content-Type': 'application/json'
                        }
                      })
                      if (!response.ok) {
                        throw new Error('CSVダウンロード失敗')
                      }
                      const blob = await response.blob()
                      const url = window.URL.createObjectURL(blob)
                      const link = document.createElement('a')
                      link.href = url
                      link.download = `kouchou_${report.slug}.csv`
                      link.click()
                      window.URL.revokeObjectURL(url)
                    } catch (error) {
                      console.error(error)
                      alert('CSVのダウンロードに失敗しました')
                    }
                  }}
                >
                  <Icon>
                    <DownloadIcon />
                  </Icon>
                </Button>
              </Tooltip>
            )}
            {report.status === 'ready' && (
              <Link href={`${process.env.NEXT_PUBLIC_CLIENT_BASEPATH}/${report.slug}`} target="_blank">
                <Button variant="ghost">
                  <ExternalLinkIcon />
                </Button>
              </Link>
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
                    if (confirm(`レポート「${report.title}」を削除してもよろしいですか？`)) {
                      try {
                        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${report.slug}`, {
                          method: 'DELETE',
                          headers: {
                            'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
                            'Content-Type': 'application/json'
                          }
                        })
                        if (response.ok) {
                          alert('レポートを削除しました')
                          window.location.reload()
                        } else {
                          alert('レポートの削除に失敗しました')
                        }
                      } catch (error) {
                        console.error(error)
                        alert('レポートの削除に失敗しました')
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
  )
}

export default function Page() {
  const [reports, setReports] = useState<Report[]>()

  useEffect(() => {
    (async () => {
      const response = await fetch(process.env.NEXT_PUBLIC_API_BASEPATH + '/admin/reports', {
        method: 'GET',
        headers: {
          'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
          'Content-Type': 'application/json'
        }
      })
      if (!response.ok) return
      setReports(await response.json())
    })()
  }, [])

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
        {reports && reports.map(report => (
          <ReportCard key={report.slug} report={report} />
        ))}
        <HStack justify="center" mt={10}>
          <Link href="/create">
            <Button size="xl">新しいレポートを作成する</Button>
          </Link>
        </HStack>
      </Box>
    </div>
  )
}
