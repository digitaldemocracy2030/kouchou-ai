# Lean で analysis-core の判定ロジックを確かめる

analysis-core のうち、外部 API を呼ばない純粋な判定ロジック 3 つを Lean 4（v4.36.0、Mathlib なし）に写し、性質を証明しています。Python のコードを Lean で直接検証することはできないので、次の 3 段で確かめます。

- **証明**（`lean/KV/*Proofs.lean`）：写したモデルについて、入力の大きさを問わず性質が成り立つことを示す。`sorry` は無い。使う公理は `propext`・`Classical.choice`・`Quot.sound` だけ（`lean/Axioms.lean`）
- **差分テスト**（`difftest.py`）：同じ乱数入力（各 1500 件、hypothesis）を本物の Python 関数と Lean のモデル（`oracle` 実行ファイル）の両方に流し、答えが一致することを見る。証明はモデルについてしか言えないので、モデルがコードとずれていないことをここで裏づける
- **全数検査**（`lean/KV/Check.lean`）：証明していない向きを、小さい入力のすべてで確かめる

CI は `.github/workflows/analysis-core-lean.yml`（必須のチェックではない）。

## 実行

```bash
cd verification/lean && lake build            # 証明の検査と oracle のビルド（elan が lean-toolchain の版を入れる）
lake env lean Axioms.lean                      # 使った公理
.lake/build/bin/oracle check 4                 # 全数検査（工程 4 個以下）
cd ../.. && pip install hypothesis && python -m pytest verification/difftest.py -q
```

## コードを変えた時

`modeled-sources.txt` に、モデルに写したファイルと、写した版の blob（`git hash-object`）を記録しています。CI は、ファイルが記録に無い版になると warning を出します（失敗にはしない）。

- 写した部分（下の各節の「写したもの」）に関わらない変更なら、`git hash-object <file>` の行を足すだけでよい
- 関わる変更なら、モデル（`lean/KV/<名前>.lean`）を直し、証明（`lean/KV/<名前>Proofs.lean`）が通るか、差分テストが一致するかを見る。差分テストが落ちたら、モデルとコードのどちらが意図どおりかを先に決める

## 1. 依存解決（`workflow/resolver.py`）

写したもの：`resolve_execution_order`（Kahn 法）、`validate_dependencies`、`_duplicate_ids`。

| 定理 | 内容 |
|---|---|
| `resolve_sound` | `resolve_execution_order` が並びを返したら、それは全工程をちょうど 1 回ずつ含み、各工程の `depends_on` はすべてその工程より前にある |
| `validate_reports_missing` | 存在しない工程への依存は、例外ではなく `validate_dependencies` のエラーの一覧に入る |
| `duplicate_id_reported` | 工程 ID の重複は、「循環」ではなく重複として報告される |

逆向き（循環が無ければ必ず並びを返す）は証明していません。全数検査で、工程 4 個以下の依存グラフ 65,536 通り（自己依存を含む）すべてで「並びを返す ⇔ 依存を守る並びが存在する」を確かめています。

モデル化の注意：`in_degree` は Int で持つ（Nat だと 0 − 1 = 0 になり、`== 0` の判定がコードとずれる）。

## 2. 再実行の判定（`core/orchestration.py` の `decide_what_to_run` と `load_specs`）

写したもの：`plan_step` の if の連鎖（順番もコードと同じ）、`build_plan`、`validate_specs_order`。ファイルの有無・前回の記録・パラメータの差分は、工程ごとの観測値 `Obs` にまとめました。`newer_deps` や `different_params` の中身はモデルに入れていません。観測値の定義とコードが一致することは、差分テストで見ています。

| 定理 | 内容 |
|---|---|
| `closure_of_loaded` | `load_specs` の検査を通った spec なら、`-o` を使わない限り、再実行される工程の下流は（無効にした工程を除き）すべて再実行される |
| `skip_sound` | さらに (hR) 各工程が実際に読む設定キーが、再実行の判定に使うキーに含まれ、(hD) 各工程とその上流が無効かどうかがその工程の判定キーだけで決まるなら、スキップされた工程の出力は今回の設定で計算し直したものと一致する |
| `unsorted_breaks_closure` / `unsorted_rejected` | spec が依存順でないと上流の再実行が下流へ伝わらない。だから `load_specs` で弾く |
| `disable_optin_keeps_stale_output` / `declaring_enabled_reruns` | `skip_sound` の前提 (hR) が要る理由。集計工程は `opinion_classification.enabled` などを読むので、それを判定に入れないと、無効に戻した時に古い分類が残る。今の spec は集計の `global_params` に入れている |

spec の `dependencies` に工程を足し引きする時、または工程が新しく設定を読むようにした時は、(hR) を満たすように判定キーを宣言してください。

## 3. クラスタの木（`hierarchical_merge_labelling.py`）

写したもの：`melt_cluster_data`、`_build_parent_child_mapping`、`_check_single_parent`、その結果の `(level, id)` での left join。`hierarchical_clusters.csv` の各行を「各層のクラスタ番号の列」とみなしています。これが `hierarchical_result.json` の clusters（root を除く）と、各意見の `cluster_ids` になります。

| 定理 | 内容 |
|---|---|
| `clusters_keys_nodup_of_singleParent` | 入れ子の検査を通れば、入れ子かどうかによらず `(level, id)` は重複しない（検査が保証すること） |
| `singleParent_of_nested` | 階層クラスタが入れ子（下の層が同じなら上の層も同じ）なら検査を通る |
| `clusters_eq` | 入れ子なら、各クラスタにちょうど 1 つの親が付く（親が null になることも無い） |
| `parent_exists` | 入れ子なら、root 以外の親は clusters の中に実在し、層が 1 つ上 |
| `cluster_ids_chain` | 入れ子なら、各意見の `cluster_ids` は root から最下層までの親子の鎖になる |
| `not_nested_duplicates` / `not_nested_rejected` | 入れ子でないと、同じクラスタが親違いで重複し、子の件数が親を超える。今は検査で止まる |

## 写していないもの

- ラベル・説明・密度、LLM の呼び出し、ファイルの読み書き
- `decide_what_to_run` の `_legacy_embeddings_rerun_reason`（2 回目の `build_plan` は `rerun` 引数として一般に扱っている）と、`different_params` / `global_params` の比較の中身
- llm_grouping が書くクラスタ（1 層だけ）
- value の「親 = 子の合計」（入れ子なら定義から明らかなので、証明していない）
