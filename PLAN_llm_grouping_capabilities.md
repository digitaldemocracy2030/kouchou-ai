# PLAN: LLMグルーピング導入とCapability自動判定

## この計画で何を変えるか（先に結論）

この計画は、意見分析の中核処理を以下の2段階で改善する。

1. 短期: 既存の表示仕様を壊さずに `llm_grouping` 分析方式を追加する  
2. 長期: 「どの可視化が使えるか」を手動設定ではなく、分析結果の実データから自動判定する

---

## 最低限の用語説明

- `extraction`: コメント本文から「個別の意見文」を抽出する処理
- `embedding`: 意見文をベクトル化する処理（意味の近さを数値化）
- `x/y`: 可視化（散布図）で使う座標
- `hierarchical_clustering`: ベクトルを使って階層的にグループ化する既存方式
- `llm_grouping`: LLMを使って意見グループを発見し、各意見を分類する新方式
- `analysis_capabilities`: 分析結果が持つ性質（例: 座標があるか、階層があるか）
- `requirements`: 可視化プラグイン側が必要とする性質
- `legacy pipeline`: 既存の固定ステップ実行経路

---

## 背景

現在の分析フローは実質的に次を前提にしている。

1. `extraction`
2. `embedding`
3. `hierarchical_clustering`
4. 後続のラベリング・集約・可視化

このため、可視化は `x/y` と階層クラスタ情報の存在を暗黙に期待する。  
一方で、分析手法としては「LLMで意見グループを発見し、そのグループへ分類する」方式を導入したい。

---

## 決定事項（この議論で確定）

1. `x/y` は `extraction` 結果を `embedding` し、次元削減して得た実座標を採用する  
2. 短期では、`llm_grouping` 方式でも既存 viewer 互換のため `cluster-level-*` と `x/y` を従来フォーマットで出力する  
3. 長期では、分析結果から `analysis_capabilities` を自動導出し、可視化プラグインの `requirements` と突合する

---

## 現状の制約

1. 実行経路の中心が `legacy pipeline` で、workflow差し替えが本番導線に未統合  
2. API/Admin の入力スキーマは `cluster` 前提で、分析モード切替フィールドがない  
3. 可視化プラグインに `requirements` 概念がなく、modeの可否判定が場当たり的

---

## ゴール

## G1（短期ゴール）

- `analysis_mode=llm_grouping` を指定して以下を実行できる
  - `extraction`
  - `embedding`（座標生成のため）
  - `llm_grouping`（グループ発見＋分類）
  - `overview`
  - `aggregation`
- 既存 viewer がエラーなく表示できる

### G1 完了条件（DoD）

- `analysis_mode` が config/API/Admin で受け渡しできる
- `llm_grouping` 実行結果で `hierarchical_result.json` が生成できる
- 既存可視化（少なくとも散布図・ツリーマップ・リスト）が描画できる

## G2（長期ゴール）

- `analysis_capabilities` を実データから自動算出して保存できる
- 可視化プラグインが `requirements` を宣言できる
- 要件不一致の mode が自動で disable される

### G2 完了条件（DoD）

- 手動設定なしで `analysis_capabilities` が生成される
- `requirements` 不一致の mode が UI で選択不可になる
- `defaultChart` が不一致なら利用可能 mode へフォールバックする

---

## スコープ

## In Scope

- analysis-core: 分析モード追加、`llm_grouping` 追加、capability導出
- api/admin: モード指定と設定受け渡し
- public-viewer: capability ベースの mode 無効化
- テスト: ユニット + 主要E2E更新

## Out of Scope（初期段階）

- 全可視化プラグインの全面再設計
- capability を使った複雑な自動レイアウト最適化
- 既存レポート全件の再生成

---

## 実装方針

## Phase 1: 短期導入（互換重視）

1. **分析モード追加**
   - `analysis_mode` を config/API/Admin に追加
   - 値: `hierarchical`（default）, `llm_grouping`

2. **`llm_grouping` ステップ導入**
   - 新ステップ（または分析プラグイン）として追加
   - 役割:
     - 意見グループ候補の発見
     - 各 `argument` のグループ分類
     - `cluster-level-*` 列生成

3. **座標は実埋め込み由来**
   - `embedding` を実行し、次元削減で `x/y` を生成
   - `hierarchical_clusters.csv` に `arg-id, argument, x, y, cluster-level-*` を出力

4. **既存下流の再利用**
   - `overview`, `aggregation` は原則既存利用
   - 互換性に必要な最小調整のみ実施

### Phase 1 完了条件

- `analysis_mode=llm_grouping` でレポート作成が完走する
- 既存 viewer で主要画面が表示できる

## Phase 2: Capability自動判定（長期基盤）

1. **capability detector 実装（analysis-core）**
   - `hierarchical_result.json` 生成後に実データを検査
   - `analysis_capabilities` を派生値として追記
   - 手入力・固定値は使わない

2. **判定ルール（初版）**
   - `has_xy`: `arguments[].x/y` が有限数
   - `has_hierarchy`: `clusters[].level/id/parent` が木構造として整合
   - `has_density_rank`: `clusters[].density_rank_percentile` が `0..1`
   - `has_multi_level`: `max(level) >= 2`
   - `has_source_url`: 有効URLが1件以上

3. **判定ポリシー**
   - 「キーがある」だけでなく値の妥当性も検証
   - 判定不能は `false` 扱い（conservative）

### Phase 2 完了条件

- 既存/新モードの双方で `analysis_capabilities` が生成される
- detector の単体テストで主要パターンを網羅できる

## Phase 3: 可視化要件との突合

1. **chart plugin manifest 拡張**
   - `requirements` を追加
   - 例: `["has_xy", "has_hierarchy"]`

2. **viewer の mode可否判定**
   - `requirements` と `analysis_capabilities` を突合
   - 不一致 mode は disable + tooltip 表示
   - `defaultChart` 不一致時は利用可能 mode へフォールバック

3. **検証二重化（推奨）**
   - 基本はサーバーが保存した `analysis_capabilities` を利用
   - 必要に応じて viewer 側でも再計算し、差分は warning として可視化

### Phase 3 完了条件

- 不適合 mode が自動的に選択不可になる
- fallback と warning の挙動がテストで保証される

---

## データ設計（案）

`hierarchical_result.json` に `analysis_capabilities` を追加する。

```json
{
  "analysis_capabilities": {
    "has_xy": true,
    "has_hierarchy": true,
    "has_density_rank": true,
    "has_multi_level": true,
    "has_source_url": false
  }
}
```

可視化プラグイン側（manifest）の要件例:

```ts
requirements: ["has_xy", "has_hierarchy"]
```

---

## 変更対象ファイル（初期候補）

## analysis-core

- `packages/analysis-core/src/analysis_core/orchestrator.py`
- `packages/analysis-core/src/analysis_core/workflows/*`（workflow分岐を採る場合）
- `packages/analysis-core/src/analysis_core/steps/*`（`llm_grouping` 追加）
- `packages/analysis-core/src/analysis_core/steps/hierarchical_aggregation.py`（capabilities追記）

## api/admin

- `apps/api/src/schemas/admin_report.py`
- `apps/api/src/services/report_launcher.py`
- `apps/admin/app/create/page.tsx`
- `apps/admin/app/create/api/createReport.ts`

## public-viewer

- `apps/public-viewer/type.ts`
- `apps/public-viewer/components/charts/plugins/types.ts`
- `apps/public-viewer/components/charts/plugins/validation.ts`
- `apps/public-viewer/components/charts/SelectChartButton.tsx`
- `apps/public-viewer/components/report/ClientContainer.tsx`

---

## テスト計画

1. **analysis-core**
   - capability detector のユニットテスト
   - `analysis_mode=llm_grouping` のスモークテスト

2. **api/admin**
   - mode指定が config へ保存されること
   - mode別の実行経路分岐テスト

3. **public-viewer**
   - `requirements` 不一致 mode が disable されること
   - `defaultChart` フォールバックテスト

4. **E2E**
   - `llm_grouping` レポートが作成・表示できること
   - 不適合可視化がUIで選択不能になること

---

## リスクと対策

1. **既存互換の破壊**
   - 対策: `analysis_mode` の default を現行 `hierarchical` のまま維持

2. **capability 判定の過検出/過少検出**
   - 対策: conservative 判定 + 代表データセットの追加テスト + warning表示

3. **運用中レポートとの混在**
   - 対策: `analysis_capabilities` 未存在時の後方互換推定ロジックを実装

---

## 未決事項

1. `llm_grouping` の内部アルゴリズム詳細（全件分類 vs 代表点分類+補完）
2. capability 判定をサーバー単独にするか、viewer再計算も必須にするか
3. workflow実行系へ全面移行する時期（legacy実行をいつ廃止するか）

---

## マイルストン（案）

1. M1: `analysis_mode` 導入 + config受け渡し
2. M2: `llm_grouping` 最小実装（実embedding座標付き）
3. M3: `analysis_capabilities` 自動導出
4. M4: 可視化 `requirements` 判定 + UI反映
5. M5: E2E整備 + ドキュメント更新

