# 将来の実装提案 (Future Implementation Proposals)

このドキュメントは、M5リファクタリング計画の Phase 3-5 で延期された機能の将来実装案をまとめたものです。

## 概要

以下の機能は、現在のリファクタリング（Phase 1-6）では対象外としましたが、将来的に需要があれば実装を検討する価値があります。

---

## 1. ワークフロー選択UI

### 背景
現在、分析パイプラインは `hierarchical` ワークフローに固定されています。Phase 3 で実装した `WorkflowEngine` とプラグインシステムにより、技術的にはカスタムワークフローを定義・実行することが可能です。

### 提案内容
管理画面（Admin UI）にワークフロー選択機能を追加し、レポート作成時に使用するワークフローを選択できるようにする。

### 実装案
1. **ワークフロー一覧API**: `GET /admin/workflows` で利用可能なワークフロー定義を返却
2. **レポート作成UIの拡張**: ワークフロー選択ドロップダウンを追加
3. **ステップ別設定UI**: 選択したワークフローのステップごとに設定をオーバーライドできるUI
4. **設定のJSON Schema駆動化**: プラグインの `config_schema` を使ってフォームを動的生成

### 影響範囲
- `apps/admin/app/create/` - レポート作成フォーム
- `apps/api/src/routers/admin_report.py` - ワークフロー一覧API
- `packages/analysis-core/` - ワークフローメタデータの公開API

### 優先度
低 - 現在の用途では単一ワークフローで十分機能している

---

## 2. `run_workflow()` への外部プラグイン読み込み統合

### 背景
`packages/analysis-core` の `run_workflow()` 関数は、現在ビルトインプラグインのみを使用します。`plugins/analysis/` に配置した外部プラグインは、明示的に `load_all_plugins()` を呼ばないと認識されません。

### 現状のコード
```python
# orchestrator.py - run_workflow()
def run_workflow(config: PipelineConfig, workflow_id: str, ...) -> Path:
    engine = WorkflowEngine()  # ビルトインのみ
    # load_all_plugins() は呼ばれない
```

### 提案内容
`run_workflow()` にオプション引数を追加し、外部プラグインディレクトリを指定できるようにする。

### 実装案
```python
def run_workflow(
    config: PipelineConfig,
    workflow_id: str,
    *,
    plugin_dirs: list[Path] | None = None,  # 追加
    ...
) -> Path:
    if plugin_dirs:
        for plugin_dir in plugin_dirs:
            load_all_plugins(plugin_dir)
    engine = WorkflowEngine()
    ...
```

### 影響範囲
- `packages/analysis-core/src/analysis_core/orchestrator.py`
- 関連テストの追加

### 優先度
中 - CLI/ライブラリユースケースでカスタムプラグインを使いたい場合に必要

---

## 3. `run_workflow()` 経由での plan 生成

### 背景
`Analysis` 画面では `result.config.plan` を参照して実行ステップを表示しています。`run()` メソッド経由では plan が生成されますが、`run_workflow()` 経由では生成されません。

### 現状
- `run()`: `normalize_config()` → plan 生成あり
- `run_workflow()`: `normalize_config()` を呼ぶが plan 生成ロジックがない

### 提案内容
`config_converter.py` の `normalize_config()` に plan 生成ロジックを追加し、`run_workflow()` 経由でも Analysis 画面が正しく動作するようにする。

### 実装案
1. `normalize_config()` でワークフロー定義から plan を自動生成
2. または `run_workflow()` の戻り値に plan を含める

### 影響範囲
- `packages/analysis-core/src/analysis_core/config_converter.py`
- `apps/admin/` の Analysis 画面

### 優先度
中 - `run_workflow()` をWebapp経路で使う場合に必要

---

## 4. visualization_config の draft/publish フロー

### 背景
M5計画では、管理者が可視化設定を「下書き（draft）」として保存し、プレビュー確認後に「公開（publish）」する2段階フローを検討していました。

### 現状の実装
簡略化し、直接保存・即時反映の単一フローで実装しました：
- `PATCH /admin/reports/{slug}/visualization-config` で直接保存
- 保存時に `invalidate_report_cache` で即座に反映

### 提案内容
より慎重な運用が必要な場合、draft/publish フローを追加する。

### 実装案
1. **設定データの分離**:
   - draft: `configs/{slug}.visualization.draft.json`
   - published: `outputs/{slug}/visualization_config.json`
2. **API追加**:
   - `PUT /admin/reports/{slug}/visualization-config/draft` - 下書き保存
   - `POST /admin/reports/{slug}/visualization-config/publish` - 公開
3. **プレビュー機能**: draft 状態でクライアント表示をプレビューできるUI

### 影響範囲
- `apps/api/src/routers/admin_report.py`
- `apps/admin/app/_components/ReportCard/VisualizationConfigDialog/`
- 新規プレビューコンポーネント

### 優先度
低 - 現在の即時反映フローで運用上の問題は報告されていない

---

## 5. report_launcher での workflow id / step config 出力

### 背景
`report_launcher.py` がパイプライン実行結果に workflow id と step config を出力すると、Analysis 画面やデバッグで便利です。

### 提案内容
`hierarchical_result.json` に以下を追加:
```json
{
  "config": {
    "workflow_id": "hierarchical",
    "step_configs": {
      "extraction": { ... },
      "embedding": { ... },
      ...
    }
  }
}
```

### 影響範囲
- `apps/api/broadlistening/pipeline/hierarchical_aggregation.py`
- `apps/api/src/services/report_launcher.py`

### 優先度
低 - 現在のデバッグには `plan` で十分

---

## 実装の前提条件

これらの機能を実装する前に、以下を確認することを推奨します:

1. **ユーザーからの需要**: 実際にこれらの機能を必要としているユーザーがいるか
2. **既存機能への影響**: 回帰テストで既存機能が壊れないことを確認
3. **運用コスト**: 機能追加による保守コストの増加

---

## 関連ドキュメント

- [M5_REFACTORING_PLAN.md](/M5_REFACTORING_PLAN.md) - 全体のリファクタリング計画
- [packages/analysis-core/docs/FAQ.md](/packages/analysis-core/docs/FAQ.md) - analysis-core FAQ
- [packages/analysis-core/docs/WHY_PLUGIN_SYSTEM.md](/packages/analysis-core/docs/WHY_PLUGIN_SYSTEM.md) - プラグインシステムの設計思想
