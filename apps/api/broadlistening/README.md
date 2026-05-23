## 概要

`apps/api/broadlistening/` は API 実行時に使う分析データ置き場です。分析ロジック本体は `packages/analysis-core/` にあり、FastAPI からのレポート生成も `python -m analysis_core` を subprocess で起動します。

Web 側の canonical artifact は `hierarchical_result.json` で、`public-viewer` がこれを描画します。CLI では必要に応じて `report.html` も生成できますが、これはローカル確認用の補助 HTML であり、API 経路では `--without-html` により生成しません。

## ディレクトリ構成

- `pipeline/configs/`: 分析設定 JSON
- `pipeline/inputs/`: 入力 CSV
- `pipeline/outputs/`: 実行結果

## 実行フロー

current 実装の `analysis-core` CLI は、以下のステップを順番に実行します。

1. **extraction**: テキストから意見を抽出
2. **embedding**: 抽出した意見の埋め込みを生成
3. **hierarchical_clustering**: 意見を階層クラスタリング
4. **hierarchical_initial_labelling**: 各クラスタの初期ラベル付け
5. **hierarchical_merge_labelling**: 階層間のラベルを調整
6. **hierarchical_overview**: クラスタ概要を生成
7. **hierarchical_aggregation**: 結果を集約し JSON を出力
8. **hierarchical_visualization**: 必要時のみ `report.html` を生成

現在の CLI canonical path は `PipelineOrchestrator.run_default()` → `run_workflow()` です。

## クレジット

本パイプラインは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports) を参考に開発されており、ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。ここに原作者の貢献に感謝の意を表します。
