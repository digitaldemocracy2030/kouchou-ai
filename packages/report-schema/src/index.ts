/**
 * @kouchou-ai/report-schema
 *
 * 広聴AIのレポートデータスキーマを定義する共通パッケージ
 */

// ============================================================================
// メタデータ
// ============================================================================

/**
 * レポートのメタデータ
 */
export type Meta = {
  /** デフォルトのメタデータかどうか */
  isDefault: boolean;
  /** レポート作成者名 */
  reporter: string;
  /** レポート作成者からのメッセージ */
  message: string;
  /** レポート作成者URL */
  webLink?: string;
  /** プライバシーポリシーURL */
  privacyLink?: string;
  /** 利用規約URL */
  termsLink?: string;
  /** ブランドカラー */
  brandColor?: string;
};

// ============================================================================
// レポート
// ============================================================================

/**
 * レポートの公開状態
 */
export enum ReportVisibility {
  PUBLIC = "public",
  PRIVATE = "private",
  UNLISTED = "unlisted",
}

/**
 * レポートのステータス
 */
export type ReportStatus = "ready" | "processing" | "error";

/**
 * レポートの基本情報
 */
export type ReportBase = {
  /** レポートのスラッグ（URL用識別子） */
  slug: string;
  /** レポートのステータス */
  status: ReportStatus;
  /** レポートのタイトル */
  title: string;
  /** レポートの説明 */
  description: string;
  /** パブリックコメント形式かどうか */
  isPubcom: boolean;
  /** 公開状態 */
  visibility: ReportVisibility;
  /** 作成日時（ISO形式の文字列） */
  createdAt?: string;
  /** トークン使用量（合計） */
  tokenUsage?: number;
  /** 入力トークン使用量 */
  tokenUsageInput?: number;
  /** 出力トークン使用量 */
  tokenUsageOutput?: number;
  /** 推定コスト（USD） */
  estimatedCost?: number;
  /** LLMプロバイダー */
  provider?: string;
  /** LLMモデル */
  model?: string;
};

/**
 * 分析完了したレポート
 */
export type ReadyReport = ReportBase & {
  status: "ready";
  analysis: {
    commentNum: number;
    argumentsNum: number;
    clusterNum: number;
  };
};

/**
 * 処理中またはエラーのレポート
 */
export type ProcessingOrErrorReport = ReportBase & {
  status: "processing" | "error";
};

/**
 * レポート型（全ステータスの union）
 */
export type Report = ReadyReport | ProcessingOrErrorReport;

// ============================================================================
// 分析結果
// ============================================================================

/**
 * 抽出された意見（Argument）
 */
export type Argument = {
  /** 意見の識別子 */
  arg_id: string;
  /** 意見の内容 */
  argument: string;
  /** 関連するコメントのID */
  comment_id: number;
  /** X座標（埋め込み後の位置情報） */
  x: number;
  /** Y座標（埋め込み後の位置情報） */
  y: number;
  /** 追加情報（数値） */
  p: number;
  /** 属するクラスタのIDリスト */
  cluster_ids: string[];
  /** 属性情報（オプション） */
  attributes?: Record<string, string | number>;
  /** ソースURL（オプション） */
  url?: string;
};

/**
 * クラスタ情報
 */
export type Cluster = {
  /** クラスタの階層レベル */
  level: number;
  /** クラスタの識別子 */
  id: string;
  /** クラスタの名前 */
  label: string;
  /** クラスタの要約 */
  takeaway: string;
  /** クラスタのサイズ・スコア */
  value: number;
  /** 親クラスタのID（ルートは空文字） */
  parent: string;
  /** 密度ランクのパーセンタイル */
  density_rank_percentile?: number | null;
  /** フィルターの結果、すべての要素が除外された場合にtrue */
  allFiltered?: boolean;
  /** フィルター対象外の場合にtrue（TreemapChartで使用） */
  filtered?: boolean;
};

/**
 * APIレスポンス用のクラスタ型
 */
export type ClusterResponse = {
  level: number;
  id: string;
  label: string;
  description: string;
  value: number;
  parent: string | null;
  density: number | null;
  density_rank: number | null;
  density_rank_percentile: number | null;
};

/**
 * クラスタ更新用の型
 */
export type ClusterUpdate = {
  id: string;
  label: string;
  description: string;
};

/**
 * コメント情報
 */
export type Comments = Record<string, { comment: string }>;

/**
 * 分析結果
 */
export type Result = {
  /** 抽出された意見のリスト */
  arguments: Argument[];
  /** クラスタ情報 */
  clusters: Cluster[];
  /** コメント情報 */
  comments: Comments;
  /** プロパティマッピング情報 */
  propertyMap: Record<string, unknown>;
  /** 翻訳情報 */
  translations: Record<string, unknown>;
  /** 解析概要 */
  overview: string;
  /** 設定情報 */
  config: Config;
  /** コメント数 */
  comment_num?: number;
  /** フィルターに一致した引数IDのリスト */
  filteredArgumentIds?: string[];
  /** レポートの可視性設定 */
  visibility?: ReportVisibility;
};

// ============================================================================
// 設定
// ============================================================================

/**
 * パイプライン設定
 */
export type Config = {
  /** 設定の名前 */
  name: string;
  /** AIに関する問い */
  question: string;
  /** 入力データの識別子 */
  input: string;
  /** 使用するモデル名 */
  model: string;
  /** イントロダクションの説明文 */
  intro: string;
  /** 結果の出力ディレクトリ名 */
  output_dir: string;
  /** 過去の設定情報 */
  previous?: Config;
  /** ローカルで埋め込みを生成するかどうか */
  is_embedded_at_local?: boolean;
  /** ソースリンク機能を有効にするかどうか */
  enable_source_link?: boolean;
  /** 抽出設定 */
  extraction: ExtractionConfig;
  /** クラスタリング設定 */
  hierarchical_clustering: HierarchicalClusteringConfig;
  /** 埋め込み設定 */
  embedding: EmbeddingConfig;
  /** 初期ラベリング設定 */
  hierarchical_initial_labelling: LabellingConfig;
  /** マージラベリング設定 */
  hierarchical_merge_labelling: LabellingConfig;
  /** 概要生成設定 */
  hierarchical_overview: OverviewConfig;
  /** 集約設定 */
  hierarchical_aggregation: AggregationConfig;
  /** 可視化設定 */
  hierarchical_visualization: VisualizationConfig;
  /** 実行計画 */
  plan: PlanStep[];
  /** 現在のステータス */
  status: string | StatusDetail;
};

/**
 * 抽出設定
 */
export type ExtractionConfig = {
  workers: number;
  limit: number;
  properties: string[] | string;
  categories: Record<string, Record<string, string>>;
  category_batch_size: number;
  source_code: string;
  prompt: string;
  model: string;
};

/**
 * クラスタリング設定
 */
export type HierarchicalClusteringConfig = {
  cluster_nums: number[];
  source_code: string;
};

/**
 * 埋め込み設定
 */
export type EmbeddingConfig = {
  model: string;
  source_code: string;
};

/**
 * ラベリング設定
 */
export type LabellingConfig = {
  workers: number;
  source_code: string;
  prompt: string;
  model: string;
};

/**
 * 概要生成設定
 */
export type OverviewConfig = {
  source_code: string;
  prompt: string;
  model: string;
};

/**
 * 集約設定
 */
export type AggregationConfig = {
  hidden_properties: Record<string, string[]>;
  source_code: string;
};

/**
 * 可視化設定
 */
export type VisualizationConfig = {
  replacements: Record<string, string[]>;
  source_code: string;
};

/**
 * 実行計画のステップ
 */
export type PlanStep = {
  step: string;
  run: boolean | string;
  reason: string;
};

/**
 * ステータスの詳細
 */
export type StatusDetail = {
  status: string;
  start_time: string;
  completed_jobs: CompletedJob[];
  lock_until: string;
  current_job: string;
  current_job_started: string;
};

/**
 * 完了したジョブ
 */
export type CompletedJob = {
  step: string;
  completed: string;
  duration: number | string;
  params: {
    workers: number;
    limit?: number | string;
    properties?: string[] | string;
    categories?: Record<string, Record<string, string>>;
    category_batch_size: number;
    source_code: string;
    prompt: string;
    model: string;
  };
};

// ============================================================================
// ロケール
// ============================================================================

/**
 * 日本語ロケール型
 */
export type JaLocaleType = {
  moduleType: "locale";
  name: string;
  dictionary: Record<string, string>;
  format: {
    days: string[];
    shortDays: string[];
    months: string[];
    shortMonths: string[];
    date: string;
  };
};

// ============================================================================
// レポート表示設定
// ============================================================================

/**
 * 利用可能なチャートタイプ
 */
export type ChartType = "scatterAll" | "scatterDensity" | "treemap";

/**
 * 散布図密度設定のパラメータ
 */
export type ScatterDensityParams = {
  /** 密度の最大閾値 */
  maxDensity?: number;
  /** 最小値の閾値 */
  minValue?: number;
};

/**
 * 表示パラメータ
 */
export type DisplayParams = {
  /** クラスターラベルを表示するかどうか */
  showClusterLabels?: boolean;
  /** 散布図密度設定 */
  scatterDensity?: ScatterDensityParams;
};

/**
 * レポート表示設定
 *
 * レポートの表示方法をカスタマイズするための設定。
 * 管理者がdraftとして保存し、publishで公開する。
 * Note: パイプラインステップ用のVisualizationConfigとは別の型。
 */
export type ReportDisplayConfig = {
  /** 設定のバージョン */
  version: string;
  /** 有効化されたチャートのリスト */
  enabledCharts: ChartType[];
  /** デフォルトで選択されるチャート */
  defaultChart?: ChartType;
  /** チャートの表示順序（指定しない場合はenabledChartsの順） */
  chartOrder?: ChartType[];
  /** 表示パラメータ */
  params?: DisplayParams;
  /** 最終更新日時（ISO形式） */
  updatedAt?: string;
  /** 最終更新者 */
  updatedBy?: string;
};

/**
 * レポート表示設定のデフォルト値
 */
export const DEFAULT_REPORT_DISPLAY_CONFIG: ReportDisplayConfig = {
  version: "1",
  enabledCharts: ["scatterAll", "scatterDensity", "treemap"],
  defaultChart: "scatterAll",
  params: {
    showClusterLabels: true,
    scatterDensity: {
      maxDensity: 0.2,
      minValue: 5,
    },
  },
};
