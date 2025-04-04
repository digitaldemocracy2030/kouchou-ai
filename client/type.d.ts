export type Meta = {
  reporter: string // レポート作成者名
  message: string // レポート作成者からのメッセージ
  webLink?: string // レポート作成者URL
  privacyLink?: string // プライバシーポリシーURL
  termsLink?: string // 利用規約URL
  brandColor?: string // ブランドカラー
}

export type Report = {
  slug: string,
  status: string,
  title: string
  description: string
  is_public?: boolean
}

export type Result = {
  arguments: Argument[] // 抽出された意見のリスト
  clusters: Cluster[] // クラスタ情報
  comments: Comments // コメント情報
  propertyMap: Record<string, any> // プロパティマッピング情報
  translations: Record<string, any> // 翻訳情報
  overview: string // 解析概要
  config: Config // 設定情報
  comment_num: number // コメント数
}

type Argument = {
  arg_id: string // 意見の識別子
  argument: string // 意見の内容
  comment_id: number // 関連するコメントの ID
  x: number // X 座標（データの位置情報）
  y: number // Y 座標（データの位置情報）
  p: number // 追加情報（数値）
  cluster_ids: string[] // 属するクラスタの ID リスト
}

export type Cluster = {
  level: number // クラスタの階層レベル
  id: string // クラスタの識別子
  label: string // クラスタの名前
  takeaway: string // クラスタの要約
  value: number // クラスタのサイズ・スコア
  parent: string // 親クラスタの ID（ルートは空文字）
  density_rank_percentile: number // 密度ランクのパーセンタイル
}

export type JaLocaleType = {
  moduleType: 'locale'
  name: string
  dictionary: Record<string, string>
  format: {
    days: string[]
    shortDays: string[]
    months: string[]
    shortMonths: string[]
    date: string
  }
}

type Comments = Record<string, { comment: string }> // コメントIDをキーに持つオブジェクト

type Config = {
  name: string // 設定の名前
  question: string // AIに関する問い
  input: string // 入力データの識別子
  model: string // 使用するモデル名
  intro: string // イントロダクションの説明文
  output_dir: string // 結果の出力ディレクトリ名
  previous?: Config // 過去の設定情報
  extraction: {
    workers: number // 並列処理数
    limit: number// データ抽出の上限数
    properties: string[] | string // 含めるプロパティのリスト（配列 or 文字列）
    categories: Record<string, Record<string, string>> // 分類情報
    category_batch_size: number // カテゴリ処理のバッチサイズ
    source_code: string // 実行するスクリプトのコード
    prompt: string // LLM に渡すプロンプト
    model: string // 使用するモデル名
  }
  hierarchical_clustering: {
    cluster_nums: number[] // クラスタ数のリスト
    source_code: string // クラスタリングのスクリプト
  }
  embedding: {
    model: string // 使用する埋め込みモデル
    source_code: string // 埋め込みを生成するスクリプト
  }
  hierarchical_initial_labelling: {
    workers: number // 並列処理数
    source_code: string // 初期ラベリングスクリプト
    prompt: string // LLM のプロンプト
    model: string // 使用するモデル
  }
  hierarchical_merge_labelling: {
    workers: number // 並列処理数
    source_code: string // マージラベリングスクリプト
    prompt: string // LLM のプロンプト
    model: string // 使用するモデル
  }
  hierarchical_overview: {
    source_code: string // 概要生成スクリプト
    prompt: string // LLM のプロンプト
    model: string // 使用するモデル
  }
  hierarchical_aggregation: {
    hidden_properties: Record<string, string[]> // 非表示プロパティ情報
    source_code: string // 集約スクリプト
  }
  hierarchical_visualization: {
    replacements: Record<string, string[]>
    source_code: string // 集約スクリプト
  }
  plan: {
    step: string // ステップ名
    run: boolean | string // 実行すべきか（真偽値 or 文字列）
    reason: string // 実行理由
  }[]
  status: string | {
    status: string // 現在の処理ステータス
    start_time: string // 開始時刻
    completed_jobs: {
      step: string
      completed: string
      duration: number | string
      params: {
        workers: number // 並列処理数
        limit?: number | string
        properties?: string[] | string
        categories?: Record<string, Record<string, string>>
        category_batch_size: number
        source_code: string
        prompt: string
        model: string
      }
    }[] // 完了したジョブのリスト
    lock_until: string // ロック解除予定時刻
    current_job: string // 現在のジョブ名
    current_job_started: string // 現在のジョブの開始時刻
  }
}
