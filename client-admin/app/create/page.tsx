'use client'

import Link from 'next/link'
import { Header } from '@/components/Header'
import {
  Box,
  Button,
  Field,
  Heading,
  HStack,
  Input,
  NativeSelect,
  Presence,
  Textarea,
  useDisclosure,
  VStack,
  Text,
  Tabs
} from '@chakra-ui/react'
import { FileUploadDropzone, FileUploadList, FileUploadRoot } from '@/components/ui/file-upload'
import { useState } from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { parseCsv, CsvData } from '@/app/create/parseCsv'
import { useRouter } from 'next/navigation'
import { toaster } from '@/components/ui/toaster'
import { extractionPrompt } from './extractionPrompt'
import { initialLabellingPrompt } from '@/app/create/initialLabellingPrompt'
import { mergeLabellingPrompt } from '@/app/create/mergeLabellingPrompt'
import { overviewPrompt } from '@/app/create/overviewPrompt'
import { ChevronRightIcon, DownloadIcon } from 'lucide-react'
import { v4 } from 'uuid'

interface SpreadsheetComment {
  id?: string
  comment: string
  source?: string | null
  url?: string | null
}

export default function Page() {
  const router = useRouter()
  const { open, onToggle } = useDisclosure()
  const [loading, setLoading] = useState<boolean>(false)
  const [input, setInput] = useState<string>(v4())
  const [importedId, setImportedId] = useState<string>('')
  const [question, setQuestion] = useState<string>('')
  const [intro, setIntro] = useState<string>('')
  const [csv, setCsv] = useState<File | null>(null)
  const [inputType, setInputType] = useState<'file' | 'spreadsheet'>('file')
  const [spreadsheetUrl, setSpreadsheetUrl] = useState<string>('')
  const [spreadsheetImported, setSpreadsheetImported] = useState<boolean>(false)
  const [spreadsheetLoading, setSpreadsheetLoading] = useState<boolean>(false)
  const [spreadsheetData, setSpreadsheetData] = useState<SpreadsheetComment[]>([])
  const [model, setModel] = useState<string>('gpt-4o-mini')
  const [clusterLv1, setClusterLv1] = useState<number>(5)
  const [clusterLv2, setClusterLv2] = useState<number>(50)
  const [workers, setWorkers] = useState<number>(30)
  const [extraction, setExtraction] = useState<string>(extractionPrompt)
  const [initialLabelling, setInitialLabelling] = useState<string>(initialLabellingPrompt)
  const [mergeLabelling, setMergeLabelling] = useState<string>(mergeLabellingPrompt)
  const [overview, setOverview] = useState<string>(overviewPrompt)
  const [isPubcomMode, setIsPubcomMode] = useState<boolean>(true)
  const [csvColumns, setCsvColumns] = useState<string[]>([])
  const [selectedCommentColumn, setSelectedCommentColumn] = useState<string>('')

  // IDのバリデーション関数
  const isValidId = (id: string): boolean => {
    return /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(id) && id.length <= 255
  }

  // IDのバリデーション結果を状態として持つ
  const [isIdValid, setIsIdValid] = useState<boolean>(true)

  // 入力変更時にバリデーションを実行
  const handleIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newId = e.target.value
    setInput(newId)
    setIsIdValid(isValidId(newId))
  }

  const canImport = spreadsheetUrl.trim() && isIdValid && !spreadsheetImported

  async function importSpreadsheet() {
    if (!canImport) {
      toaster.create({
        type: 'error',
        title: '入力エラー',
        description: !isIdValid
          ? 'IDは英小文字、数字、ハイフンのみ使用できます'
          : 'スプレッドシートのURLを入力してください',
      })
      return
    }

    setSpreadsheetLoading(true)
    try {
      const response = await fetch(process.env.NEXT_PUBLIC_API_BASEPATH + '/admin/spreadsheet/import', {
        method: 'POST',
        headers: {
          'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: spreadsheetUrl,
          file_name: input
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '不明なエラーが発生しました')
      }

      await response.json()

      setImportedId(input)

      // スプレッドシートのデータを取得
      const commentResponse = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/spreadsheet/data/${input}`, {
        headers: {
          'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
        },
      })

      if (!commentResponse.ok) {
        throw new Error('スプレッドシートデータの取得に失敗しました')
      }

      const commentData = await commentResponse.json()
      setSpreadsheetData(commentData.comments)

      if (commentData.comments.length > 0) {
        const columns = Object.keys(commentData.comments[0])
        setCsvColumns(columns)
        if (columns.includes('comment')) {
          setSelectedCommentColumn('comment')
        }
      }
      
      if (commentData.comments.length > 0) {
        setCsvColumns(Object.keys(commentData.comments[0]))
      }
      
      toaster.create({
        type: 'success',
        title: '成功',
        description: `スプレッドシートのデータ ${commentData.comments.length} 件を取得しました`,
      })
      setSpreadsheetImported(true)
    } catch (e) {
      console.error(e)

      // エラーメッセージを解析して、より適切な短いメッセージに変換
      const errorMessage = e instanceof Error ? e.message : '不明なエラーが発生しました'
      let displayErrorMessage = ''

      // URLやアクセス権限のエラー
      if (errorMessage.includes('Unauthorized') || errorMessage.includes('401')) {
        displayErrorMessage = 'スプレッドシートへのアクセス権限がありません。公開設定を確認してください。'
      }
      // 存在しないシートなど
      else if (errorMessage.includes('404') || errorMessage.includes('Not Found')) {
        displayErrorMessage = 'スプレッドシートが見つかりません。URLを確認してください。'
      }
      // スプレッドシート形式の問題
      else if (errorMessage.includes('comment') || errorMessage.includes('カラム')) {
        displayErrorMessage = 'スプレッドシートの形式が正しくありません。commentカラムが必要です。'
      }
      // その他のエラー
      else {
        displayErrorMessage = 'スプレッドシートの取得に失敗しました。URLと公開設定を確認してください。'
      }

      toaster.create({
        type: 'error',
        title: 'データ取得エラー',
        description: displayErrorMessage,
      })
      setSpreadsheetImported(false)
    } finally {
      setSpreadsheetLoading(false)
    }
  }

  async function onSubmit() {
    setLoading(true)

    const commonCheck = [
      /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(input),
      question.length > 0,
      intro.length > 0,
      clusterLv1 > 0,
      clusterLv2 > 0,
      model.length > 0,
      extraction.length > 0,
    ].every(Boolean)

    const sourceCheck =
      (inputType === 'file' && !!csv) ||
      (inputType === 'spreadsheet' && spreadsheetImported)

    if (!commonCheck || !sourceCheck) {
      toaster.create({
        type: 'error',
        title: '入力エラー',
        description: '全ての項目が入力されているか確認してください',
      })
      setLoading(false)
      return
    }
    if (csvColumns.length > 0 && !selectedCommentColumn) {
      toaster.create({
        type: 'error',
        title: 'カラム未選択',
        description: 'コメントカラムを選択してください',
      })
      setLoading(false)
      return
    }
    
    let comments: CsvData[] = []
    try {
      if (inputType === 'file' && csv) {
        const parsed = await parseCsv(csv)
        comments = parsed.map((row, index) => ({
          id: `csv-${index + 1}`,
          comment: ((row as unknown) as Record<string, unknown>)[selectedCommentColumn] as string,
          source: null,
          url: null
        }))
        if (comments.length < clusterLv2) {
          const confirmProceed = window.confirm(
            `csvファイルの行数 (${comments.length}) が設定された意見グループ数 (${clusterLv2}) を下回っています。このまま続けますか？
    \n※コメントから抽出される意見が設定された意見グループ数に満たない場合、処理中にエラーになる可能性があります（一つのコメントから複数の意見が抽出されることもあるため、問題ない場合もあります）。
    \n意見グループ数を変更する場合は、「AI詳細設定」を開いてください。`
          )
          if (!confirmProceed) {
            setLoading(false)
            return
          }
        }
      } else if (inputType === 'spreadsheet' && spreadsheetImported) {
        comments = spreadsheetData.map((row, index) => ({
          id: row.id || `spreadsheet-${index + 1}`,
          comment: ((row as unknown) as Record<string, unknown>)[selectedCommentColumn] as string,
          source: row.source || null,
          url: row.url || null
        }))
      }
    } catch (e) {
      toaster.create({
        type: 'error',
        title: 'データの読み込みに失敗しました',
        description: e as string,
      })
      setLoading(false)
      return
    }
    
    try {
      const payload = {
        input,
        question,
        intro,
        comments,
        cluster: [clusterLv1, clusterLv2],
        model,
        workers,
        prompt: {
          extraction,
          initialLabelling,
          mergeLabelling,
          overview
        },
        is_pubcom: isPubcomMode
      }
    
      console.log('送信されるJSON:', payload)

      const response = await fetch(process.env.NEXT_PUBLIC_API_BASEPATH + '/admin/reports', {
        method: 'POST',
        headers: {
          'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          input,
          question,
          intro,
          comments,
          cluster: [clusterLv1, clusterLv2],
          model,
          workers,
          prompt: {
            extraction,
            initialLabelling,
            mergeLabelling,
            overview
          },
          is_pubcom: isPubcomMode,
          inputType
        })
      })
      if (!response.ok) {
        throw new Error(response.statusText)
      }
      toaster.create({
        duration: 5000,
        type: 'success',
        title: 'レポート作成を開始しました',
      })
      router.replace('/')
    } catch (e) {
      console.error(e)
      toaster.create({
        duration: 5000,
        type: 'error',
        title: 'レポート作成に失敗しました',
        description: '問題が解決しない場合は開発者に問い合わせください',
      })
    } finally {
      setLoading(false)
    }
  }
  const handleTabValueChange = (details: { value: string }) => {
    const newType = details.value as 'file' | 'spreadsheet'
    setInputType(newType)
  
    if (newType === 'file' && csv) {
      // CSVのカラムを再構築
      parseCsv(csv).then(parsed => {
        if (parsed.length > 0) {
          const columns = Object.keys(parsed[0])
          setCsvColumns(columns)
          if (columns.includes('comment')) {
            setSelectedCommentColumn('comment')
          }
        }
      })
    } else if (newType === 'spreadsheet' && spreadsheetData.length > 0) {
      // スプレッドシートのカラムを再構築
      const columns = Object.keys(spreadsheetData[0])
      setCsvColumns(columns)
      if (columns.includes('comment')) {
        setSelectedCommentColumn('comment')
      }
    } else {
      // データがない場合はカラムリセット
      setCsvColumns([])
      setSelectedCommentColumn('')
    }
  }
  
  

  return (
    <div className={'container'}>
      <Header />
      <Box mx={'auto'} maxW={'800px'}>
        <Heading textAlign={'center'} my={10}>新しいレポートを作成する</Heading>
        <VStack gap={5}>
          <Field.Root>
            <Field.Label>タイトル</Field.Label>
            <Input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="例：人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？"
            />
            <Field.HelperText>レポートのタイトルを記載します</Field.HelperText>
          </Field.Root>
          <Field.Root>
            <Field.Label>調査概要</Field.Label>
            <Input
              value={intro}
              onChange={e => setIntro(e.target.value)}
              placeholder="例：このAI生成レポートは、パブリックコメントにおいて寄せられた意見に基づいています。"
            />
            <Field.HelperText>コメントの集計期間や、コメントの収集元など、調査の概要を記載します</Field.HelperText>
          </Field.Root>
          <Field.Root>
            <Field.Label>入力データ</Field.Label>
            <Tabs.Root
              defaultValue="file"
              value={inputType}
              onValueChange={handleTabValueChange}
              variant="enclosed"
              width="100%"
            >
              <Tabs.List>
                <Tabs.Trigger value="file">CSVファイル</Tabs.Trigger>
                <Tabs.Trigger value="spreadsheet">Googleスプレッドシート</Tabs.Trigger>
                <Tabs.Indicator />
              </Tabs.List>

              <Box p={4}>
                <Tabs.Content value="file">
                  <VStack alignItems="stretch" w="full">
                    <Link href="/sample_comments.csv"
                      download
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        marginLeft: '8px',
                        textDecoration: 'underline',
                        fontSize: '0.8rem',
                      }}
                    >
                      <DownloadIcon size={14} />
                      サンプルCSVをダウンロード
                    </Link>
                    <FileUploadRoot
                      w={'full'}
                      alignItems="stretch"
                      accept={['text/csv']}
                      inputProps={{ multiple: false }}
                      onFileChange={async (e) => {
                        const file = e.acceptedFiles[0]
                        setCsv(file)
                        if (file) {
                          const parsed = await parseCsv(file)
                          if (parsed.length > 0) {
                            const columns = Object.keys(parsed[0])
                            setCsvColumns(columns)
                            if (columns.includes('comment')) {
                              setSelectedCommentColumn('comment')
                            }
                          }
                        }
                      }}
                    >
                      <Box opacity={csv ? 0.5 : 1} pointerEvents={csv ? 'none' : 'auto'}>
                        <FileUploadDropzone
                          label="分析するコメントファイルを選択してください"
                          description=".csv"
                        />
                      </Box>
                      <FileUploadList
                        clearable={true}
                        onRemove={() => setCsv(null)}
                      />
                    </FileUploadRoot>
                    {csvColumns.length > 0 && (
                      <Field.Root mt={4}>
                        <Field.Label>コメントカラム選択</Field.Label>
                        <NativeSelect.Root w={'60%'}>
                          <NativeSelect.Field
                            value={selectedCommentColumn}
                            onChange={(e) => setSelectedCommentColumn(e.target.value)}
                          >
                            <option value="">選択してください</option>
                            {csvColumns.map((col) => (
                              <option key={col} value={col}>{col}</option>
                            ))}
                          </NativeSelect.Field>
                          <NativeSelect.Indicator />
                        </NativeSelect.Root>
                        <Field.HelperText>
                          分析対象のコメントが含まれるカラムを選んでください（それ以外のカラムは無視されます）。
                        </Field.HelperText>
                      </Field.Root>
                    )}
                  </VStack>
                </Tabs.Content>

                <Tabs.Content value="spreadsheet">
                  <VStack alignItems="stretch" w="full" gap={4}>
                    <Field.Root>
                      <Field.Label>スプレッドシートURL</Field.Label>
                      <HStack w="full" flexDir={['column', 'column', 'row']}
                        alignItems={['stretch', 'stretch', 'center']} 
                        gap={[2, 2, 4]}
                      >
                        <Input
                          flex="1"
                          value={spreadsheetUrl}
                          onChange={e => setSpreadsheetUrl(e.target.value)}
                          placeholder="https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit"
                          disabled={spreadsheetImported}  // インポート済みの場合はURL入力も無効化
                        />
                        <Button
                          onClick={importSpreadsheet}
                          loading={spreadsheetLoading}
                          disabled={!canImport}
                          whiteSpace="nowrap"
                          width={['full', 'full', 'auto']}
                        >
                          {spreadsheetImported ? '取得済み' : 'データを取得'}
                        </Button>
                      </HStack>
                      <Field.HelperText>
                        公開されているGoogleスプレッドシートのURLを入力してください<br />
                      </Field.HelperText>
                      {csvColumns.length > 0 && (
                        <Field.Root mt={4}>
                          <Field.Label>コメントカラム選択</Field.Label>
                          <NativeSelect.Root w={'60%'}>
                            <NativeSelect.Field
                              value={selectedCommentColumn}
                              onChange={(e) => setSelectedCommentColumn(e.target.value)}
                            >
                              <option value="">選択してください</option>
                              {csvColumns.map((col) => (
                                <option key={col} value={col}>{col}</option>
                              ))}
                            </NativeSelect.Field>
                            <NativeSelect.Indicator />
                          </NativeSelect.Root>
                          <Field.HelperText>
                            分析対象のコメントが含まれるカラムを選んでください（それ以外のカラムは無視されます）。
                          </Field.HelperText>
                        </Field.Root>
                      )}

                    </Field.Root>
                    {spreadsheetImported && (
                      <Text color="green.500" fontSize="sm">
                        スプレッドシートのデータ {spreadsheetData.length} 件を取得しました
                      </Text>
                    )}

                    {/* スプレッドシートデータ再取得のためのボタンを追加 */}
                    {spreadsheetImported && (
                      <Button
                        onClick={async () => {
                          try {
                            setSpreadsheetLoading(true)
                            // サーバー側のデータを削除するAPI呼び出し - インポート時のIDを使用
                            const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/inputs/${importedId}`, {
                              method: 'DELETE',
                              headers: {
                                'x-api-key': process.env.NEXT_PUBLIC_ADMIN_API_KEY || '',
                              },
                            })

                            if (!response.ok) {
                              throw new Error('データのクリアに失敗しました')
                            }

                            toaster.create({
                              type: 'success',
                              title: '成功',
                              description: 'データをクリアしました',
                            })
                          } catch (e) {
                            console.error(e)
                            toaster.create({
                              type: 'warning',
                              title: '警告',
                              description: 'サーバー側のデータクリアに失敗しましたが、入力をリセットしました',
                            })
                          } finally {
                            // UIの状態をリセット
                            setSpreadsheetImported(false)
                            setSpreadsheetData([])
                            setSpreadsheetLoading(false)
                            setImportedId('')
                            setSpreadsheetUrl('')
                            setSelectedCommentColumn('')
                            setCsvColumns([])
                          }
                        }}
                        colorScheme="red"
                        variant="outline"
                        size="sm"
                        loading={spreadsheetLoading}
                        loadingText="クリア中..."
                      >
                        データをクリアして再入力
                      </Button>
                    )}
                  </VStack>
                </Tabs.Content>
              </Box>
            </Tabs.Root>
          </Field.Root>
          <HStack justify={'flex-end'} w={'full'}>
            <Button onClick={onToggle} variant={'outline'} w={'200px'}>
              AI詳細設定 (オプション)
            </Button>
          </HStack>
          <Presence present={open} w={'full'}>
            <VStack gap={10}>
              <Field.Root>
                <Field.Label>ID</Field.Label>
                <Input
                  w={'40%'}
                  value={input}
                  onChange={handleIdChange}
                  placeholder="例：example"
                  aria-invalid={!isIdValid}
                  borderColor={!isIdValid ? 'red.300' : undefined}
                  _hover={!isIdValid ? { borderColor: 'red.400' } : undefined}
                />
                {!isIdValid && (
                  <Text color="red.500" fontSize="sm" mt={1}>
                    IDは英小文字、数字、ハイフンのみ使用できます
                  </Text>
                )}
                <Field.HelperText>英字小文字と数字とハイフンのみ(URLで利用されます)</Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Checkbox
                  checked={isPubcomMode}
                  onCheckedChange={(details) => {
                    const { checked } = details
                    if (checked === 'indeterminate') return
                    setIsPubcomMode(checked)
                  }}
                >
                パブコメモード
                </Checkbox>
                <Field.HelperText>
                元のコメントと要約された意見をCSV形式で出力します。完成したCSVファイルはレポート一覧ページからダウンロードできます。
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>意見グループ数</Field.Label>
                <HStack w={'100%'}>
                  <Button
                    onClick={() => {
                      setClusterLv1(Math.max(2, clusterLv1 - 1))
                    }}
                    variant="outline"
                  >
                    -
                  </Button>
                  <Input
                    type="number"
                    value={clusterLv1.toString()}
                    min={2}
                    max={10}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      if (!isNaN(v)) {
                        setClusterLv1(Math.max(2, Math.min(10, v)))
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      setClusterLv1(Math.min(10, clusterLv1 + 1))
                    }}
                    variant="outline"
                  >
                    +
                  </Button>
                  <ChevronRightIcon width="100px"/>
                  <Button
                    onClick={() => {
                      setClusterLv2(Math.max(2, clusterLv2 - 1))
                    }}
                    variant="outline"
                  >
                    -
                  </Button>
                  <Input
                    type="number"
                    value={clusterLv2.toString()}
                    min={2}
                    max={1000}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      if (!isNaN(v)) {
                        setClusterLv2(Math.max(2, Math.min(1000, v)))
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      setClusterLv2(Math.min(1000, clusterLv2 + 1))
                    }}
                    variant="outline"
                  >
                    +
                  </Button>
                </HStack>
                <Field.HelperText>
                  階層ごとの意見グループ生成数です
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>並列実行数</Field.Label>
                <HStack>
                  <Button
                    onClick={() => {
                      setWorkers(Math.max(1, workers - 1))
                    }}
                    variant="outline"
                  >
                    -
                  </Button>
                  <Input
                    type="number"
                    value={workers.toString()}
                    min={1}
                    max={100}
                    onChange={(e) => {
                      const v = Number(e.target.value)
                      if (!isNaN(v)) {
                        setWorkers(Math.max(1, Math.min(100, v)))
                      }
                    }}
                  />
                  <Button
                    onClick={() => {
                      setWorkers(Math.min(100, workers + 1))
                    }}
                    variant="outline"
                  >
                    +
                  </Button>
                </HStack>
                <Field.HelperText>
                  OpenAI APIの並列実行数です。値を大きくすることでレポート出力が速くなりますが、OpenAIアカウントのTierによってはレートリミットの上限に到達し、レポート出力が失敗する可能性があります。
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>AIモデル</Field.Label>
                <NativeSelect.Root w={'40%'}>
                  <NativeSelect.Field value={model} onChange={(e) => setModel(e.target.value)}>
                    <option value={'gpt-4o-mini'}>OpenAI GPT-4o mini</option>
                    <option value={'gpt-4o'}>OpenAI GPT-4o</option>
                    <option value={'o3-mini'}>OpenAI o3-mini</option>
                  </NativeSelect.Field>
                  <NativeSelect.Indicator />
                </NativeSelect.Root>
                <Field.HelperText>
                  {model === 'gpt-4o-mini' && 'GPT-4o mini：最も安価に利用できるモデルです。価格の詳細はOpenAIが公開しているAPI料金のページをご参照ください。'}
                  {model === 'gpt-4o' && 'GPT-4o：gpt-4o-miniと比較して高性能なモデルです。性能は高くなりますが、gpt-4o-miniと比較してOpenAI APIの料金は高くなります。'}
                  {model === 'o3-mini' && 'o3-mini：gpt-4oよりも高度な推論能力を備えたモデルです。性能はより高くなりますが、gpt-4oと比較してOpenAI APIの料金は高くなります。'}
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>抽出プロンプト</Field.Label>
                <Textarea
                  h={'150px'}
                  value={extraction}
                  onChange={(e) => setExtraction(e.target.value)}
                />
                <Field.HelperText>
                  AIに提示する抽出プロンプトです(通常は変更不要です)
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>初期ラベリングプロンプト</Field.Label>
                <Textarea
                  h={'150px'}
                  value={initialLabelling}
                  onChange={(e) => setInitialLabelling(e.target.value)}
                />
                <Field.HelperText>
                  AIに提示する初期ラベリングプロンプトです(通常は変更不要です)
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>統合ラベリングプロンプト</Field.Label>
                <Textarea
                  h={'150px'}
                  value={mergeLabelling}
                  onChange={(e) => setMergeLabelling(e.target.value)}
                />
                <Field.HelperText>
                  AIに提示する統合ラベリングプロンプトです(通常は変更不要です)
                </Field.HelperText>
              </Field.Root>
              <Field.Root>
                <Field.Label>要約プロンプト</Field.Label>
                <Textarea
                  h={'150px'}
                  value={overview}
                  onChange={(e) => setOverview(e.target.value)}
                />
                <Field.HelperText>
                  AIに提示する要約プロンプトです(通常は変更不要です)
                </Field.HelperText>
              </Field.Root>
            </VStack>
          </Presence>
          <Button
            mt={10}
            className={'gradientBg shadow'}
            size={'2xl'}
            w={'300px'}
            onClick={onSubmit}
            loading={loading}
          >レポート作成を開始</Button>
        </VStack>
      </Box>
    </div>
  )
}
