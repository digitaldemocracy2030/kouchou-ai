# レポート複製・再利用機能 計画

## 背景
- Issue #19 では、設定の一部だけ変えて再実行できる「レポート複製・再利用」機能が求められている。
- 現状は config から再実行はできるが、API/UI から複製する導線はない。
- `analysis-core` は出力ディレクトリに `hierarchical_status.json` がある場合、前回実行を参照してステップをスキップできる。

## 目的
- 既存レポートを新しい slug で複製し、元レポートは変更しない。
- タイトルやクラスタ数など小さな変更を許容する。
- 既存成果物を再利用し、LLM/embedding のコストを削減する。
- 管理者のみ利用可能で、元レポートの追跡性を確保する。

## 重要な方針 (最優先事項)
- 最優先はレポート再利用、特に「要約/解説プロンプト修正 → 概要だけ再生成」。
- 上書きは禁止: `newSlug` が既に存在する場合は必ず 409。`deleted` でも再利用不可 (再利用したい場合は完全削除/別slug)。
- 概要は常に再生成: 複製時に `hierarchical_overview.txt` を必ず削除 (トグルは設けない)。
- 再利用はデフォルト ON。手動トグルは再利用のみで、再実行ステップは差分から表示する。
- 排他制御は `newSlug` 単位で行い、`analysis-core` 起動完了でロックを解放する。

## 非目的
- 公開ユーザーが複製をする。
- プロジェクトやテナントを跨ぐ複製。
- 複製時の入力データ差し替え。

## 現状整理 (主要ファイル)
- 設定: `configs/{slug}.json` は `apps/api/src/services/report_launcher.py` で作成。
- 入力: `inputs/{slug}.csv` を extraction / aggregation が参照。
- 出力: `outputs/{slug}/` に各ステップ成果物と `hierarchical_status.json`。
- 管理: `data/report_status.json` を `apps/api/src/services/report_status.py` が管理。
- ストレージ同期: `apps/api/src/services/report_sync.py` が不要成果物を削除。

## 設計概要
1. 管理APIに複製エンドポイントを追加: `POST /admin/reports/{slug}/duplicate`。
2. 新しい slug を作成し、入力/出力をコピーして新 config を書き込む。
3. `hierarchical_status.json` をコピーしてスキップ判定を有効化。
4. `hierarchical_result.json` を削除し、集計は必ず再実行。
5. `analysis-core` を新 config で起動する (ReportInput は不要)。

## 詳細実装計画 (最優先: 要約プロンプト修正で再生成)
狙い: 既存成果物を最大限再利用しつつ、**要約/解説プロンプト変更時は概要だけ再生成**できる状態を最短で実現する。

### フェーズ 1: 最短到達 (要約プロンプト変更フローを動かす)
1. API: `POST /admin/reports/{slug}/duplicate` を実装し、`overrides` で「要約/解説プロンプト」だけ差し替え可能にする。
2. 複製処理:
   - `configs/{source}.json` を読み込み `overrides` を適用して `configs/{new}.json` を作成。
   - `inputs/{new}.csv` をコピーし、`outputs/{new}/` に必要成果物をコピー。
   - `hierarchical_status.json` をコピーして `previous` 判定を有効化。
   - **複製時は常に `hierarchical_overview.txt` を削除**して再生成を強制。
   - `hierarchical_result.json` は常に削除し、集計は必ず再実行。
3. UI: 管理画面の複製ダイアログに「要約/解説プロンプト」入力欄を用意。
4. UI: 「この変更で再実行されるステップ」を表示 (overview は常に再実行されることを明示)。

### フェーズ 2: 再利用の安定化 (差分判定の明確化)
1. 変更差分から再実行ステップを算出するロジックを追加。
   - 入力/設定が変わっていなければ再利用する (analysis-core と同じ判定に合わせる)。
   - 差分がある場合は UI に「再実行ステップ」を明示する (トグルは出さない)。
2. overview は常に再実行する (複製時に `hierarchical_overview.txt` を削除)。
   - `analysis-core` の params 判定に合致することを確認し、overview 再生成が確実に走るようにする。
3. 再実行判定の根拠をログ/レスポンスに含め、運用上トレースできるようにする。

### フェーズ 3: 競合・運用・UXの強化
1. TOCTOU 対策のロック/マーカーを実装 (newSlug 単位の原子チェック)。
2. `source_slug` を保存し、一覧で複製元を追跡可能にする。
3. ストレージ利用状況の可視化 + ゴミ箱一括削除を追加。

### 実装ポイント (要約プロンプト変更の最短経路)
- 再利用ファイルは保持し、**削除は overview と result のみに限定**する。
- 既存成果物がローカルに無い場合はストレージから取得してから複製を行う。
- `reuse.enabled` は既定 ON とし、UI では「overview は常に再実行」と表示する。

## API 設計
エンドポイント:
- `POST /admin/reports/{slug}/duplicate`

リクエスト例:
```json
{
  "newSlug": "report-2025-07-dup",
  "overrides": {
    "question": "New question",
    "intro": "New intro",
    "cluster": [5, 10],
    "model": "gpt-4o-mini",
    "provider": "openai"
  },
  "reuse": {
    "enabled": true
  }
}
```

レスポンス例:
```json
{
  "success": true,
  "report": {
    "slug": "report-2025-07-dup",
    "status": "processing"
  }
}
```

補足:
- `overrides` は source config に部分適用する。
- `newSlug` は省略可能。省略時はサーバー側で一意な slug を生成し、レスポンスで返す。
- `reuse.enabled=false` の場合は成果物コピーなしでフル再実行。
- 複製時は常に `hierarchical_overview.txt` を削除して再生成する (トグルは設けない)。
- 冪等キーによる再利用はサポートしない。`newSlug` が既に存在する場合は **必ず 409** (上書き禁止)。

## ユーザーの実行フロー (解説プロンプトだけ再生成したい場合)
目的: 既存レポートの内容は維持しつつ、解説/概要の生成プロンプトだけ差し替えて再生成する。

1. 管理画面で対象レポートを開き、「複製」を選択する。
2. 新しい slug を入力する (例: `{slug}-overview-rev1`)。空欄の場合は自動生成する (例: `{slug}-copy-{YYYYMMDD}`)。
3. 複製ダイアログの「解説/概要プロンプト」欄に新しいプロンプトを入力する。
4. 再利用トグルは ON にする (既存成果物を最大限再利用)。既定値も ON とする。
5. 送信すると新しいレポートが `processing` で作成され、概要ステップだけが再実行される。
6. 完了後、新しいレポートで解説が更新されていることを確認する (元レポートは変更されない)。

補足:
- 解説/概要プロンプトの差し替えのみであれば、抽出/埋め込み/クラスタ等は再利用される想定。
- 再利用トグルを OFF にすると全工程が再実行されるため、意図しないコスト増につながる。

## ユーザーの実行フロー (クラスタリングのパラメータを変える場合)
目的: 抽出/埋め込みは再利用しつつ、クラスタリング以降だけ再実行して結果を変える。

1. 管理画面で対象レポートを開き、「複製」を選択する。
2. 新しい slug を入力する (例: `{slug}-cluster-rev1`)。空欄の場合は自動生成する (例: `{slug}-copy-{YYYYMMDD}`)。
3. 複製ダイアログの「クラスタ数」や「クラスタリング関連パラメータ」を変更する (例: `cluster: [5, 10]` の変更)。
4. 再利用トグルは ON にする (抽出/埋め込み/入力を再利用)。
5. 送信すると新しいレポートが `processing` で作成され、クラスタリング以降のステップが再実行される。
6. 完了後、新しいレポートでクラスタ構造と集計結果が更新されていることを確認する (元レポートは変更されない)。

補足:
- クラスタ関連の params が変わるため、`hierarchical_clusters.csv` と下流の `hierarchical_*` が再生成される想定。
- 抽出/埋め込み成果物が存在する場合はそれらを再利用でき、コストを抑えられる。

## ユーザーの実行フロー (extraction の prompt を変える場合)
目的: 入力は再利用しつつ、抽出結果から下流を再生成する。

1. 管理画面で対象レポートを開き、「複製」を選択する。
2. 新しい slug を入力する (例: `{slug}-extract-rev1`)。空欄の場合は自動生成する (例: `{slug}-copy-{YYYYMMDD}`)。
3. 複製ダイアログの「extraction プロンプト」欄で新しいプロンプトに変更する。
4. 再利用トグルは ON にする (入力は再利用、抽出以降は再実行)。
5. 送信すると新しいレポートが `processing` で作成され、抽出ステップから再実行される。
6. 完了後、新しいレポートで抽出結果・クラスタ・解説が更新されていることを確認する (元レポートは変更されない)。

補足:
- extraction の params が変わるため、`args.csv` / `relations.csv` が再生成され、埋め込み以降も再実行される想定。
- 入力ファイルが同一であれば取得コストは抑えられるが、LLM コストは増える点に注意。

## 再利用方針 (analysis-core)
`analysis-core` がステップをスキップする条件:
- `hierarchical_status.json` が存在し、`previous` として読み込まれる。
- 新 output dir にステップ成果物が存在する。
- ステップの params が `previous` と一致する。

再利用を成立させるための操作:
- `outputs/{source}/hierarchical_status.json` を `outputs/{new}/` にコピー。
- 必要な成果物を `outputs/{new}/` にコピー。
- `hierarchical_result.json` を削除し、集計を強制実行。
- 複製時は常に `hierarchical_overview.txt` を削除して再生成する。

再利用の優先度:
- 入力取得が高コストなケース (特に Twitter 取得) では入力データの再利用を最優先する。
- LLM コストが高い `extraction` と `embedding` は次点で最優先に再利用する。

再利用対象として保持すべき成果物:
- `args.csv`, `relations.csv`
- `embeddings.pkl`
- `hierarchical_clusters.csv`
- `hierarchical_initial_labels.csv`
- `hierarchical_merge_labels.csv`
- `hierarchical_overview.txt`
最低限の再利用セット (error からの複製でも使える前提):
- 入力: `inputs/{slug}.csv` (取得コストが高い入力は最優先で再利用)
- 抽出済み: `args.csv`, `relations.csv`
- 埋め込み: `embeddings.pkl`

## ストレージ/クリーンアップ変更
`ReportSyncService.PRESERVED_REPORT_FILES` に追加:
- `embeddings.pkl`
- `hierarchical_initial_labels.csv`
- 既存の `.json`, `args.csv`, `relations.csv`, `hierarchical_clusters.csv`, `hierarchical_merge_labels.csv`, `hierarchical_overview.txt` は維持。
意図:
- 複製/再利用時に必要な中間成果物は「消されないこと」を保証するため、`PRESERVED_REPORT_FILES` に含める。
- 特に `embeddings.pkl` は再生成コストが高く、欠損すると再利用効果がほぼ失われるため必須。
- `hierarchical_initial_labels.csv` は再集計や可視化の再生成で参照されるため保持対象に含める。
- `ReportSyncService` は未使用成果物を削除するため、ここに含めない成果物は複製で欠落する恐れがある。
- ただし肥大化しやすい成果物 (巨大な一時ファイル等) は対象外とし、保持対象は「再利用に直結するもの」に限定する。


追加ユーティリティ:
- `download_input_file(slug)`
- `download_report_artifacts(slug, patterns)`
役割:
- ローカルに入力や成果物が存在しない場合でも複製が成立するよう、ストレージから必要ファイルを取得する。
- `download_input_file(slug)` は `inputs/{slug}.csv` がローカルにない場合にストレージから取得し、存在チェックと併せて再利用する。
- `download_report_artifacts(slug, patterns)` は `outputs/{slug}/` 配下の成果物を対象パターンで一括取得する。`patterns` には `embeddings.pkl` などのファイル名配列または glob を渡せる想定。
- いずれも「存在していればスキップ、なければ取得」を基本方針とし、重複ダウンロードを避ける。


## バックエンド処理フロー (複製)
1. 管理者 API キーを検証。
2. source レポートが `ready` または `error` であることを確認 (`processing` は不可)。
3. `newSlug` を確定する (未指定なら自動生成)。
4. `newSlug` が未使用かつ安全な形式かを確認。
   - `configs/{newSlug}.json` / `inputs/{newSlug}.csv` / `outputs/{newSlug}/` / `report_status.json` のいずれかに存在があれば **409**。
5. 競合防止のため `newSlug` に紐づくロック/マーカーを原子的に作成する (例: `outputs/{newSlug}/.duplicate.lock` か DB のユニーク行)。
   - 既に存在する場合は TOCTOU (Time Of Check / Time Of Use: 「存在確認」と「作成」の間に他リクエストが割り込む競合) とみなし即座に 409 を返す (同一リクエストの再送でも再利用しない)。
6. `configs/{source}.json` を読み込み。
7. `overrides` を適用し `name` と `input` を `newSlug` に更新。
7.1 `source_slug` を config と status に記録する。
8. 入力ファイル存在を確認 (必要ならストレージから取得)。
9. `inputs/{newSlug}.csv` を作成 (source をコピー)。
10. `outputs/{newSlug}/` を作成し、必要成果物をコピー。
11. `hierarchical_status.json` をコピーして再利用を有効化。
12. `hierarchical_result.json` と `hierarchical_overview.txt` を削除 (概要は常に再生成)。
13. `report_status.json` に `status=processing` で追加 (ロック取得後にのみ書き込む)。
14. config path を受け取る新 helper で `analysis-core` を起動。

### ロック機構の詳細 (TOCTOU 対策)
- 排他の範囲:
  - `configs/`・`inputs/`・`outputs/` の作成/コピー/削除と `report_status.json` 更新、および `analysis-core` 起動までを排他対象とする。
- ロック作成失敗時の処理:
  - ロック/マーカー作成が失敗した場合は **即座に 409** を返す。
  - 冪等キーによる再利用は行わないため、再送でも成功扱いにしない。
  - 単純な「存在チェック」だけでは同時実行を防げないため、**原子的なロック/一意制約で二重作成を防止**する。
- ロック保持期間 / 解放タイミング:
  - **成功時は `analysis-core` のプロセス起動が完了した時点でロックを解放**する (推奨)。`analysis-core` は非同期で実行される。
  - 失敗時は、起動失敗の検知・後片付け後にロックを解放する。
  - TTL を設定し (例: 10 分)、作成時刻をロックに記録する。
  - もし「実行完了までロック保持」を採用する場合は TTL を十分長くする必要があり、ロックの役割が肥大化するため採用しない。
- クラッシュ時のクリーンアップ:
  - 既存ロックが TTL 超過の場合は「古いロック」とみなし、**部分成果物を削除してからロックを解除**して再実行を許可する。
  - 部分成果物には `configs/{newSlug}.json`, `inputs/{newSlug}.csv`, `outputs/{newSlug}/` を含む。

### エラーハンドリング
- 複製元が想定外の状態の場合:
  - `ready` / `error` 以外 (例: `processing`, `deleted`) は **409** を返し、UI はエラー表示とする。
- `newSlug` の重複:
  - 既存の slug が確認できた場合は **409** を返し、いかなる上書きも禁止する (`deleted` も再利用不可)。
- ファイルコピー途中での失敗:
  - 途中失敗時は **部分成果物を削除**し、ロックを解放して 500 を返す。
  - `report_status.json` が作成済みの場合は `error` に更新し、失敗理由を記録する。
- `analysis-core` 起動失敗時:
  - `report_status.json` を `error` に更新し、失敗理由を記録する。
  - ロックを解放する (以後の再実行は削除→再作成で対応)。

## バックエンド変更点
- 新スキーマ: `ReportDuplicateRequest` / `ReportDuplicateResponse`。
- `Report` メタデータに `source_slug` を追加 (複製元の slug、通常作成時は `null`)。
- ストレージ利用状況取得 API を追加 (利用可能容量 / 使用容量 / ゴミ箱占有量)。
- ゴミ箱一括削除 API を追加 (削除済みレポートの成果物を一括削除)。
- 新サービス: `duplicate_report()` を `apps/api/src/services/report_launcher.py` か新規ファイルに追加。
- `apps/api/src/services/report_status.py` に `add_new_report_to_status_from_config()` を追加。
- `apps/api/src/routers/admin_report.py` に複製エンドポイントを追加。
- `ReportSyncService` に成果物保持/取得を追加。

## フロントエンド計画 (管理画面)
- `apps/admin/app/_components/ReportCard/ActionMenu/ActionMenu.tsx` に「複製」アクション追加。
- レポート一覧で `source_slug` がある場合は「複製済み」を示すアイコンを表示し、ホバー/クリックで複製元の slug を確認できるようにする。
  - 例: コピーアイコン + tooltip に `source_slug` を表示。
  - クリック時は複製元レポート詳細に遷移できる導線を用意する。
- ストレージ利用状況の表示:
  - 利用可能容量 / 使用容量 / ゴミ箱占有量を表示する。
  - 「ゴミ箱を空にする」操作を追加し、削除済みレポートの成果物を一括削除できる。
- 複製ダイアログ:
  - 新 slug (例: `"{slug}-copy-{YYYYMMDD}"`)
  - タイトル/概要
  - クラスタ数
  - model/provider
  - 再利用トグル
    - 再利用トグル:
      - ON: 既存成果物をコピーし、`analysis-core` のスキップ機構を活かす (`reuse.enabled=true`)。
      - OFF: 入力はコピーするが成果物はコピーせず、フル再実行 (`reuse.enabled=false`)。
    - デフォルトは再利用=ON (コスト削減優先) とする。
- 送信後は `processing` 表示で既存進捗UIを利用。

## テスト
バックエンド:
- temp dir と fake storage を使った複製フローの単体テスト。
- 新 config の値とファイルコピーの検証。
- `hierarchical_result.json` が削除されて集計が再実行されること。
フロントエンド:
- ダイアログ表示/バリデーション/API 呼び出しテスト。

## 受け入れ条件
- 複製したレポートが管理画面に `processing` で表示される。
- 複製レポートには `source_slug` が保存され、管理画面の一覧から複製元を確認できる。
- メタデータ変更のみなら集計が再実行され、結果に反映される。
- クラスタ数変更なら抽出は再利用され、クラスタ以降が再実行される。
- プロンプト変更なら依存ステップのみ再実行される。
- 元レポートのファイルが変更されない。
- `error` レポートから複製した場合でも、存在する成果物は再利用される。
- `extraction`/`embedding` 成果物が存在する場合は、それらを再利用してコスト削減できる。
- 管理画面でストレージの利用可能容量・使用容量・ゴミ箱占有量が確認できる。
- 管理画面からゴミ箱を空にでき、削除済みレポートの成果物が削除される。

## 仕様決定
- 再利用のデフォルト範囲: 設定/入力が変わっていない限り再利用する (analysis-core と同じ自動判定に従う)。
- 中間成果物の保持期間: 再利用に必要なファイルは基本は無期限で保持する。不要な一時ファイルは対象外。削除ポリシーは「容量逼迫時のみ別途判断」とする。
- `extraction`/`embedding` の成果物が欠けている場合: 欠けているステップは再実行する。
- UI の詳細オプション: 「概要再生成」「抽出再実行」などの手動トグルは出さない。
  - `previous` と入力/設定の差分に基づき、どのステップが再実行されるかを UI 上でわかりやすく表示する。
  - 例: 「この変更により再実行されるステップ: extraction → embedding → clustering → overview」
