# Storage Snapshot Operations

このページは、Azure Blob Storage を canonical store として使う現在の広聴AIで、
ローカルファイルシステムとの間でデータを行き来させる補助スクリプトの使い分けをまとめたものです。

## 何が canonical か

現在の通常運用では、レポートの canonical store は public `/reports` API ではなく
Azure Blob Storage です。生成後の成果物は `ReportSyncService` で storage に同期され、
API 起動時は `initialize_from_storage()` で status / reports / configs / inputs を復元します。

したがって、運用上の backup / restore は API scrape ではなく storage 直接操作を基準にします。

## スクリプト一覧

### 1. 接続確認

```bash
cd apps/api
rye run python scripts/test_storage.py
```

用途:
- storage client を初期化できるか確認する
- テストファイルを upload できるか確認する
- 同じ blob を download して内容一致するか確認する

これは health check です。レポート全件の退避や復元には使いません。

### 2. Storage からローカルへ復元

```bash
python tools/scripts/download_reports_from_azure.py
```

特定 slug だけ復元する場合:

```bash
python tools/scripts/download_reports_from_azure.py --slug your-report-slug
```

用途:
- Azure Blob Storage 上の canonical data をローカルファイルシステムへ落とす
- `status / reports / configs / inputs` を current layout に合わせて復元する
- deploy 前退避、ローカル調査、移行作業の基点に使う

### 3. ローカルから Storage へアップロード

```bash
python tools/scripts/upload_reports_to_azure.py
```

用途:
- ローカルにあるレポートデータを Azure Blob Storage へアップロードする
- 既存のローカル成果物を storage-backed 運用へ移行する

注意:
- この script は移行用途です。通常の分析実行後同期は `ReportSyncService` が担当します
- current implementation は主に `outputs/` と `status/` を対象にしているため、必要に応じて `configs/` / `inputs/` も含めた運用確認をしてください

## 使い分け

### 新規環境を立てた直後

1. `scripts/test_storage.py` で read/write を確認
2. 必要なら `download_reports_from_azure.py` で既存データを復元

### 既存 Azure 環境を壊す前に退避したい

1. `download_reports_from_azure.py` で storage snapshot をローカルへ落とす
2. その後に resource group cleanup や再構築を行う

### ローカルにしかない成果物を storage に寄せたい

1. `upload_reports_to_azure.py` を使う
2. 必要に応じて API 再起動または `initialize_from_storage()` で反映を確認する

## なぜ `fetch_reports.py` を使わないか

旧 `fetch_reports.py` は public `/reports` と `/reports/{slug}` を scrape する方式でした。
この方式では private / unlisted レポートを扱えず、canonical store も API 側に見えてしまいます。

現在は Blob Storage が本線なので、

- health check は `scripts/test_storage.py`
- restore は `download_reports_from_azure.py`
- migration upload は `upload_reports_to_azure.py`

に役割を分けています。
