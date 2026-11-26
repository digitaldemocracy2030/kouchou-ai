import KV.Resolver
/-
クラスタの木の組み立て（`hierarchical_merge_labelling.py` の `melt_cluster_data` と
`_build_parent_child_mapping` と、その結果の `(level, id)` での left join。
`hierarchical_aggregation.py` の `_build_cluster_value` はこれに root "0" を足し、
`_build_arguments` は各意見の `cluster_ids` を `["0", 第1層, …, 第L層]` にする）を写したモデル。

コードとの対応
- `hierarchical_clusters.csv` の各行（意見）を `Row`、その `cluster-level-{i+1}-id` を `r.getD i 0` とする。
  id はコードでは `"{level}_{番号}"` の文字列で、層が違えば別の id になる。モデルでは (層, 番号) の組で表す。
- polars の `unique()` は順序を保たないが、ここで示す性質は順序によらない。モデルは最初に出た順。
- ラベル・説明・密度は木の形に関わらないので捨てた。
- `cluster_id_columns[0]` を第 1 層とみなすコードの前提（列が層の順に並ぶ）はそのまま置く。
-/
namespace KV.Tree

open KV.Resolver (uniq)

abbrev Row := List Nat

/-- 親の参照。root は id "0"。`missing` は left join で親が見つからず null になった場合 -/
inductive PRef where
  | root
  | node (level id : Nat)
  | missing
deriving Repr, DecidableEq

structure PEntry where
  level : Nat
  id : Nat
  parent : PRef
deriving Repr, DecidableEq

structure Cl where
  level : Nat
  id : Nat
  value : Nat
  parent : PRef
deriving Repr, DecidableEq

/-- 第 i+1 層の列 -/
def col (rows : List Row) (i : Nat) : List Nat := rows.map (·.getD i 0)

/-- 第 i+1 層のクラスタ c に属する意見の、第 i+2 層の id（unique） -/
def children (rows : List Row) (i c : Nat) : List Nat :=
  uniq ((rows.filter (fun r => r.getD i 0 == c)).map (·.getD (i + 1) 0))

/-- `_build_parent_child_mapping` -/
def parentMap (rows : List Row) (L : Nat) : List PEntry :=
  (uniq (col rows 0)).map (fun c => ⟨1, c, .root⟩) ++
  (List.range (L - 1)).flatMap (fun i =>
    (uniq (col rows i)).flatMap (fun c => (children rows i c).map (fun ch => ⟨i + 2, ch, .node (i + 1) c⟩)))

/-- `_check_single_parent`：親の表で、どの (level, id) も 1 件だけ（2 件以上なら ValueError で止まる） -/
def singleParent (rows : List Row) (L : Nat) : Bool :=
  (parentMap rows L).all (fun p =>
    decide (((parentMap rows L).filter (fun q => q.level == p.level && q.id == p.id)).length ≤ 1))

/-- `melt_cluster_data`：(level, id, value=件数) -/
def melt (rows : List Row) (L : Nat) : List (Nat × Nat × Nat) :=
  (List.range L).flatMap (fun i => (uniq (col rows i)).map (fun c => (i + 1, c, (col rows i).count c)))

/-- `melted_df.join(parent_child_df, on=["level", "id"], how="left")` -/
def clusters (rows : List Row) (L : Nat) : List Cl :=
  (melt rows L).flatMap (fun e =>
    match (parentMap rows L).filter (fun p => p.level == e.1 && p.id == e.2.1) with
    | [] => [⟨e.1, e.2.1, e.2.2, .missing⟩]
    | ps => ps.map (fun p => ⟨e.1, e.2.1, e.2.2, p.parent⟩))

/-- 各意見の `cluster_ids`（root を除く）：第 j 層の (j, id) -/
def clusterIds (r : Row) (L : Nat) : List (Nat × Nat) := (List.range L).map (fun i => (i + 1, r.getD i 0))

/-- 下の層の id が同じなら、1 つ上の層の id も同じ（階層クラスタが入れ子） -/
def Nested (rows : List Row) (L : Nat) : Prop :=
  ∀ r ∈ rows, ∀ r' ∈ rows, ∀ i, i + 1 < L → r.getD (i + 1) 0 = r'.getD (i + 1) 0 → r.getD i 0 = r'.getD i 0

/-- 第 lv 層の c の親（入れ子なら、c に属するどの意見から引いても同じ） -/
def parentOf (rows : List Row) (lv c : Nat) : PRef :=
  if lv = 1 then .root
  else match rows.find? (fun r => r.getD (lv - 1) 0 == c) with
    | some r => .node (lv - 1) (r.getD (lv - 2) 0)
    | none => .missing

end KV.Tree
