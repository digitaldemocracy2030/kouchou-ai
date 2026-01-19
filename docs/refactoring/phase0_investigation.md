# Phase 0: 現状把握・棚卸し調査結果

## 1. エントリポイントとビルド経路

### サービス構成 (compose.yaml)

| サービス | ポート | ディレクトリ | 説明 |
|---------|-------|-------------|------|
| api | 8000 | server/ | FastAPI バックエンド |
| client | 3000 | client/ | Next.js レポート閲覧 |
| client-admin | 4000 | client-admin/ | Next.js 管理画面 |
| client-static-build | 3200 | client-static-build/ | 静的ビルドサービス |
| ollama (optional) | 11434 | - | ローカルLLM |

### Makefile コマンド

#### ローカル開発
- `make build` / `make up` - Docker環境のビルド・起動
- `make client-setup` - クライアント環境セットアップ
- `make client-dev` - 開発サーバー起動（client + client-admin + dummy-server）
- `make test/api` - APIテスト実行
- `make lint/api-check` / `make lint/api-format` - Linting

#### Azure関連
- `make azure-setup-all` - 完全セットアップ
- `make azure-build` / `make azure-push` / `make azure-deploy` - デプロイフロー
- `make azure-update-deployment` - 既存環境の更新

### scripts/ ディレクトリ
- `fetch_reports.py` - レポートのバックアップ取得
- `upload_reports_to_azure.py` - Azureへのレポートアップロード
- `assign_storage_role.sh` - ストレージロール割り当て

---

## 2. パイプライン構造

### エントリポイント
- `server/broadlistening/pipeline/hierarchical_main.py` - メインオーケストレーター
- `server/src/services/report_launcher.py` - API からの呼び出し元

### ステップ一覧 (hierarchical_specs.json)

| ステップ | 出力ファイル | LLM使用 | 依存ステップ |
|---------|-------------|---------|-------------|
| extraction | args.csv | Yes | - |
| embedding | embeddings.pkl | No | extraction |
| hierarchical_clustering | hierarchical_clusters.csv | No | embedding |
| hierarchical_initial_labelling | hierarchical_initial_labels.csv | Yes | hierarchical_clustering |
| hierarchical_merge_labelling | hierarchical_merge_labels.csv | Yes | hierarchical_initial_labelling |
| hierarchical_overview | hierarchical_overview.txt | Yes | hierarchical_merge_labelling |
| hierarchical_aggregation | hierarchical_result.json | No | 複数 |
| hierarchical_visualization | report/ | No | hierarchical_aggregation |

### ハードコードされたステップ名の場所
- `client-admin/app/_components/ReportCard/ProgressSteps/ProgressSteps.tsx:8-17`
  - 固定の `steps` 配列でステップ名と表示名をマッピング

---

## 3. 結果JSON構造 (hierarchical_result.json)

```typescript
{
  arguments: Argument[];      // 抽出された意見リスト
  clusters: Cluster[];        // クラスタ情報
  comments: Comments;         // コメント情報（現在未使用）
  propertyMap: Record<string, any>;  // プロパティマッピング
  translations: Record<string, any>; // 翻訳情報
  overview: string;           // 概要テキスト
  config: Config;            // パイプライン設定（全ステップのソースコード/プロンプト含む）
  comment_num: number;       // コメント数
}
```

### Argument 型
```typescript
{
  arg_id: string;
  argument: string;
  x: number;
  y: number;
  p: number;
  cluster_ids: string[];
  attributes?: Record<string, string | number>;
  url?: string;
}
```

### Cluster 型
```typescript
{
  level: number;
  id: string;
  label: string;
  takeaway: string;
  value: number;
  parent: string;
  density_rank_percentile: number | null;
}
```

---

## 4. チャート種別のハードコード

### client/components/charts/SelectChartButton.tsx
```typescript
const items = [
  { value: "scatterAll", label: "全体" },
  { value: "scatterDensity", label: "濃い意見" },
  { value: "treemap", label: "階層" },
];
```

### client/components/report/ClientContainer.tsx（初期値）
- `selectedChart: "scatterAll"`
- `showClusterLabels: true`
- `maxDensity: 0.2`
- `minValue: 5`
- `treemapLevel: "0"`

---

## 5. 型定義の重複

### 重複している型（client/type.ts と client-admin/type.d.ts）

| 型名 | 重複状況 | 差異 |
|-----|---------|-----|
| Meta | 完全重複 | なし |
| ReportVisibility | 完全重複 | なし |
| Report | 部分重複 | client-admin には analysis 情報追加 |
| Result | 部分重複 | client には filteredArgumentIds, visibility 追加 |
| Argument | 部分重複 | client-admin には attributes, url がない |
| Cluster | 部分重複 | client-admin には density_rank_percentile, allFiltered, filtered がない |
| Comments | 完全重複 | なし |
| Config | 部分重複 | client には is_embedded_at_local, enable_source_link 追加 |

---

## 6. UIコンポーネントの重複

### client/components/ui/ と client-admin/components/ui/ の重複ファイル
- button.tsx
- checkbox.tsx
- close-button.tsx
- dialog.tsx
- file-upload.tsx
- icon-button.tsx
- link.tsx
- menu.tsx
- native-select.tsx
- provider.tsx
- radio-card.tsx
- tooltip.tsx

これらは Chakra UI ベースのラッパーコンポーネントで、ほぼ同一の実装。

---

## 7. 改善が必要な箇所（Phase 1以降で対応）

### 優先度: 高
1. **型定義の統一** → `packages/report-schema` へ移動
2. **UIコンポーネントの共通化** → `packages/ui-shared` へ移動
3. **ステップ名のハードコード除去** → API から動的取得

### 優先度: 中
1. **チャート種別のハードコード除去** → 可視化プラグインレジストリ導入
2. **パイプライン設定の分離** → ワークフロー定義ファイル

### 優先度: 低
1. **scripts/ の整理** → tools/scripts/ へ移動
2. **experimental/ の整理** → experiments/ へ移動

---

## 8. 次のステップ (Phase 1)

Phase 1 では以下のディレクトリ構成への移行を実施:

```
kouchou-ai/
├── apps/
│   ├── api/              # server → apps/api
│   ├── public-viewer/    # client → apps/public-viewer
│   ├── admin/            # client-admin → apps/admin
│   └── static-site-builder/  # client-static-build → apps/static-site-builder
├── packages/
│   ├── analysis-core/    # 新規：パイプライン実行基盤
│   ├── report-schema/    # 新規：共通型定義
│   └── ui-shared/        # 新規：共通UIコンポーネント
├── plugins/
│   ├── analysis/         # 新規：分析プラグイン
│   └── visualization/    # 新規：可視化プラグイン
├── tools/
│   └── scripts/          # scripts/ を移動
├── experiments/          # experimental/ を移動
└── docs/
```
