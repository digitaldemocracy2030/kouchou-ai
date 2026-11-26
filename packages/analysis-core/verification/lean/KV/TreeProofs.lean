import KV.Tree
import KV.ResolverProofs

namespace KV.Tree

open KV.Resolver (uniq mem_uniq nodup_uniq)

/-! ## リストの補題 -/

theorem flatMap_single {α β : Type} [DecidableEq α] :
    ∀ {l : List α} {k : α} (g : α → List β), l.Nodup → k ∈ l → (∀ i ∈ l, i ≠ k → g i = []) →
      l.flatMap g = g k
  | [], _, _, _, hk, _ => by simp at hk
  | a :: l, k, g, hn, hk, hz => by
    rw [List.nodup_cons] at hn
    simp only [List.flatMap_cons]
    by_cases hak : a = k
    · subst hak
      have : l.flatMap g = [] := by
        rw [List.flatMap_eq_nil_iff]
        intro i hi; exact hz i (by simp [hi]) (fun e => hn.1 (e ▸ hi))
      simp [this]
    · have hk' : k ∈ l := by simp at hk; rcases hk with rfl | h; exact absurd rfl hak; exact h
      rw [hz a (by simp) hak, flatMap_single g hn.2 hk' (fun i hi => hz i (by simp [hi]))]
      simp

theorem flatMap_singleton_eq_map {α β : Type} :
    ∀ {l : List α} (g : α → List β) (f : α → β), (∀ x ∈ l, g x = [f x]) → l.flatMap g = l.map f
  | [], _, _, _ => rfl
  | a :: l, g, f, h => by
    simp only [List.flatMap_cons, List.map_cons]
    rw [h a (by simp), flatMap_singleton_eq_map g f (fun x hx => h x (by simp [hx]))]
    rfl

theorem filter_single {α : Type} [DecidableEq α] :
    ∀ {l : List α} {x : α} (q : α → Bool), l.Nodup → x ∈ l → (∀ y ∈ l, q y = true ↔ y = x) → l.filter q = [x]
  | [], _, _, _, hx, _ => by simp at hx
  | a :: l, x, q, hn, hx, hq => by
    rw [List.nodup_cons] at hn
    by_cases hax : a = x
    · subst hax
      have hz : l.filter q = [] := by
        rw [List.filter_eq_nil_iff]
        intro y hy hqy
        exact hn.1 (((hq y (by simp [hy])).1 hqy) ▸ hy)
      simp [List.filter_cons, (hq a (by simp)).2 rfl, hz]
    · have hx' : x ∈ l := by
        simp at hx; rcases hx with h | h
        · exact absurd h.symm hax
        · exact h
      have hqa : q a = false := by
        cases h : q a
        · rfl
        · exact absurd ((hq a (by simp)).1 h) hax
      simp [List.filter_cons, hqa, filter_single q hn.2 hx' (fun y hy => hq y (by simp [hy]))]

theorem mem_col {rows : List Row} {i c : Nat} : c ∈ col rows i ↔ ∃ r ∈ rows, r.getD i 0 = c := by
  simp [col]

theorem mem_children {rows : List Row} {i c ch : Nat} :
    ch ∈ children rows i c ↔ ∃ r ∈ rows, r.getD i 0 = c ∧ r.getD (i + 1) 0 = ch := by
  simp only [children, mem_uniq, List.mem_map, List.mem_filter, beq_iff_eq]
  constructor
  · rintro ⟨r, ⟨hr, hc⟩, hch⟩; exact ⟨r, hr, hc, hch⟩
  · rintro ⟨r, hr, hc, hch⟩; exact ⟨r, ⟨hr, hc⟩, hch⟩

theorem mem_melt {rows : List Row} {L : Nat} {e : Nat × Nat × Nat} :
    e ∈ melt rows L ↔ ∃ i, i < L ∧ e.2.1 ∈ col rows i ∧ e = (i + 1, e.2.1, (col rows i).count e.2.1) := by
  simp only [melt, List.mem_flatMap, List.mem_range, List.mem_map, mem_uniq]
  constructor
  · rintro ⟨i, hi, c, hc, rfl⟩; exact ⟨i, hi, hc, rfl⟩
  · rintro ⟨i, hi, hc, he⟩; exact ⟨i, hi, e.2.1, hc, he.symm⟩

/-! ## 親の表の 1 件 -/

theorem filter_parentMap_level1 (rows : List Row) (L c : Nat) (hc : c ∈ col rows 0) :
    (parentMap rows L).filter (fun p => p.level == 1 && p.id == c) = [⟨1, c, .root⟩] := by
  unfold parentMap
  rw [List.filter_append]
  have hB : ((List.range (L - 1)).flatMap (fun i =>
      (uniq (col rows i)).flatMap (fun c => (children rows i c).map (fun ch => (⟨i + 2, ch, .node (i + 1) c⟩ : PEntry))))).filter
      (fun p => p.level == 1 && p.id == c) = [] := by
    rw [List.filter_eq_nil_iff]
    intro p hp
    simp only [List.mem_flatMap, List.mem_map] at hp
    obtain ⟨i, _, c', _, ch, _, rfl⟩ := hp
    simp
  rw [hB, List.append_nil, List.filter_map,
    filter_single _ (nodup_uniq _) (mem_uniq.2 hc) (fun y _ => by simp)]
  rfl

theorem filter_parentMap_level (rows : List Row) (L : Nat) (hN : Nested rows L) (k : Nat) (hk : k + 1 < L)
    (r : Row) (hr : r ∈ rows) :
    (parentMap rows L).filter (fun p => p.level == k + 2 && p.id == r.getD (k + 1) 0) =
      [⟨k + 2, r.getD (k + 1) 0, .node (k + 1) (r.getD k 0)⟩] := by
  unfold parentMap
  rw [List.filter_append]
  have hA : ((uniq (col rows 0)).map (fun c => (⟨1, c, .root⟩ : PEntry))).filter
      (fun p => p.level == k + 2 && p.id == r.getD (k + 1) 0) = [] := by
    rw [List.filter_eq_nil_iff]
    intro p hp
    simp only [List.mem_map] at hp
    obtain ⟨c', _, rfl⟩ := hp
    simp
  rw [hA, List.nil_append, List.filter_flatMap]
  rw [flatMap_single (l := List.range (L - 1)) (k := k) _ List.nodup_range (List.mem_range.2 (by omega))]
  · rw [List.filter_flatMap]
    rw [flatMap_single _ (nodup_uniq _) (mem_uniq.2 (mem_col.2 ⟨r, hr, rfl⟩))]
    · -- c' = r[k] の子の中で id が r[k+1] のもの
      have hmem : r.getD (k + 1) 0 ∈ children rows k (r.getD k 0) := mem_children.2 ⟨r, hr, rfl, rfl⟩
      have hn : (children rows k (r.getD k 0)).Nodup := nodup_uniq _
      rw [List.filter_map, filter_single _ hn hmem (fun y _ => by simp)]
      rfl
    · -- 入れ子なので、id が r[k+1] の子を持つのは r[k] だけ
      intro c' _ hc'
      rw [List.filter_eq_nil_iff]
      intro p hp
      simp only [List.mem_map] at hp
      obtain ⟨ch, hch, rfl⟩ := hp
      obtain ⟨r', hr', hr'c, hr'ch⟩ := mem_children.1 hch
      simp only [Bool.and_eq_true, beq_iff_eq, not_and, true_implies]
      intro hid
      apply hc'
      rw [← hr'c]
      exact hN r' hr' r hr k hk (hr'ch.trans hid)
  · intro i _ hik
    rw [List.filter_eq_nil_iff]
    intro p hp
    simp only [List.mem_flatMap, List.mem_map] at hp
    obtain ⟨c', _, ch, _, rfl⟩ := hp
    simp only [Bool.and_eq_true, beq_iff_eq, not_and]
    intro h; omega

/-! ## 主定理 -/

theorem parentOf_eq (rows : List Row) (L : Nat) (hN : Nested rows L) (k : Nat) (hk : k + 1 < L)
    (r : Row) (hr : r ∈ rows) :
    parentOf rows (k + 2) (r.getD (k + 1) 0) = .node (k + 1) (r.getD k 0) := by
  unfold parentOf
  rw [if_neg (by omega)]
  have e1 : k + 2 - 1 = k + 1 := by omega
  have e2 : k + 2 - 2 = k := by omega
  rw [e1, e2]
  have : (rows.find? (fun r' => r'.getD (k + 1) 0 == r.getD (k + 1) 0)).isSome := by
    rw [List.find?_isSome]; exact ⟨r, hr, by simp⟩
  obtain ⟨r', hf⟩ := Option.isSome_iff_exists.1 this
  rw [hf]
  have hr' := List.mem_of_find?_eq_some hf
  have he := List.find?_some hf
  simp only [beq_iff_eq] at he
  simp only [PRef.node.injEq, true_and]
  exact hN r' hr' r hr k hk he

/-- 入れ子なら、clusters は melt の各クラスタにちょうど 1 つの親を付けたものになる
（同じクラスタが親違いで重複して出ることも、親が null になることも無い） -/
theorem clusters_eq (rows : List Row) (L : Nat) (hN : Nested rows L) :
    clusters rows L = (melt rows L).map (fun e => ⟨e.1, e.2.1, e.2.2, parentOf rows e.1 e.2.1⟩) := by
  unfold clusters
  apply flatMap_singleton_eq_map
  intro e he
  obtain ⟨i, hi, hc, hee⟩ := mem_melt.1 he
  obtain ⟨r, hr, hrc⟩ := mem_col.1 hc
  rw [hee]; simp only
  cases i with
  | zero =>
    rw [filter_parentMap_level1 rows L e.2.1 hc]
    simp [parentOf]
  | succ k =>
    rw [← hrc, filter_parentMap_level rows L hN k hi r hr, parentOf_eq rows L hN k hi r hr]
    rfl

theorem nodup_map_pair (a : Nat) : ∀ {l : List Nat}, l.Nodup → (l.map (fun c => (a, c))).Nodup
  | [], _ => by simp
  | x :: l, h => by
    rw [List.nodup_cons] at h
    simp only [List.map_cons, List.nodup_cons, List.mem_map, Prod.mk.injEq, true_and, not_exists, not_and]
    exact ⟨fun y hy e => h.1 (e ▸ hy), nodup_map_pair a h.2⟩

theorem melt_succ (rows : List Row) (n : Nat) :
    melt rows (n + 1) = melt rows n ++ (uniq (col rows n)).map (fun c => (n + 1, c, (col rows n).count c)) := by
  simp [melt, List.range_succ, List.flatMap_append]

theorem melt_keys_nodup (rows : List Row) (L : Nat) : ((melt rows L).map (fun e => (e.1, e.2.1))).Nodup := by
  induction L with
  | zero => simp [melt]
  | succ n ih =>
    rw [melt_succ, List.map_append, List.nodup_append]
    refine ⟨ih, ?_, ?_⟩
    · rw [List.map_map]
      exact nodup_map_pair (n + 1) (nodup_uniq _)
    · intro a ha b hb hab
      subst hab
      simp only [List.mem_map] at ha hb
      obtain ⟨e, he, rfl⟩ := ha
      obtain ⟨c, hc, he'⟩ := hb
      obtain ⟨c0, _, rfl⟩ := hc
      obtain ⟨i, hi, _, hee⟩ := mem_melt.1 he
      have h1 : e.1 = i + 1 := by rw [hee]
      have h2 : e.1 = n + 1 := by
        have := congrArg Prod.fst he'; simp at this; omega
      omega

/-- 入れ子なら、`(level, id)` は clusters の中で重複しない -/
theorem clusters_keys_nodup (rows : List Row) (L : Nat) (hN : Nested rows L) :
    ((clusters rows L).map (fun x => (x.level, x.id))).Nodup := by
  rw [clusters_eq rows L hN, List.map_map]
  exact melt_keys_nodup rows L

/-- 入れ子なら、各意見の cluster_ids は親子の鎖になる：第 1 層の親は root、第 k+2 層の親は第 k+1 層 -/
theorem cluster_ids_chain (rows : List Row) (L : Nat) (hN : Nested rows L) (r : Row) (hr : r ∈ rows) :
    (∀ x ∈ clusters rows L, x.level = 1 → x.parent = .root) ∧
    (∀ k, k + 1 < L → ∀ x ∈ clusters rows L, x.level = k + 2 → x.id = r.getD (k + 1) 0 →
      x.parent = .node (k + 1) (r.getD k 0)) := by
  rw [clusters_eq rows L hN]
  constructor
  · intro x hx hl
    simp only [List.mem_map] at hx
    obtain ⟨e, _, rfl⟩ := hx
    simp only at hl ⊢
    simp [parentOf, hl]
  · intro k hk x hx hl hid
    simp only [List.mem_map] at hx
    obtain ⟨e, _, rfl⟩ := hx
    simp only at hl hid ⊢
    rw [hl, hid]
    exact parentOf_eq rows L hN k hk r hr

/-- 入れ子なら、root 以外の親はすべて clusters の中に実在し、層が 1 つ上 -/
theorem parent_exists (rows : List Row) (L : Nat) (hN : Nested rows L) :
    ∀ x ∈ clusters rows L, x.parent = .root ∨
      ∃ y ∈ clusters rows L, x.parent = .node y.level y.id ∧ x.level = y.level + 1 := by
  intro x hx
  have hx' := hx
  rw [clusters_eq rows L hN] at hx
  simp only [List.mem_map] at hx
  obtain ⟨e, he, rfl⟩ := hx
  obtain ⟨i, hi, hc, hee⟩ := mem_melt.1 he
  obtain ⟨r, hr, hrc⟩ := mem_col.1 hc
  cases i with
  | zero => left; rw [hee]; simp [parentOf]
  | succ k =>
    right
    rw [hee]; simp only
    rw [← hrc, parentOf_eq rows L hN k hi r hr]
    refine ⟨⟨k + 1, r.getD k 0, (col rows k).count (r.getD k 0), parentOf rows (k + 1) (r.getD k 0)⟩, ?_, rfl, rfl⟩
    rw [clusters_eq rows L hN, List.mem_map]
    refine ⟨(k + 1, r.getD k 0, (col rows k).count (r.getD k 0)), ?_, rfl⟩
    exact mem_melt.2 ⟨k, by omega, mem_col.2 ⟨r, hr, rfl⟩, rfl⟩

/-! ## 入れ子の検査（`_check_single_parent`） -/

/-- 入れ子なら検査を通る（今の hierarchical_clustering の出力は止まらない） -/
theorem singleParent_of_nested (rows : List Row) (L : Nat) (hN : Nested rows L) : singleParent rows L = true := by
  unfold singleParent
  rw [List.all_eq_true]
  intro p hp
  have hp' := hp
  unfold parentMap at hp'
  simp only [List.mem_append, List.mem_map, List.mem_flatMap, List.mem_range] at hp'
  rcases hp' with ⟨c, hc, rfl⟩ | ⟨k, hk, c, _, ch, hch, rfl⟩
  · rw [filter_parentMap_level1 rows L c (mem_uniq.1 hc)]; simp
  · obtain ⟨r, hr, _, rfl⟩ := mem_children.1 hch
    rw [filter_parentMap_level rows L hN k (by omega) r hr]; simp

/-- 検査を通れば、入れ子かどうかによらず、clusters の (level, id) は melt と同じ並びになり重複しない
（検査が保証すること） -/
theorem clusters_keys_of_singleParent (rows : List Row) (L : Nat) (h : singleParent rows L = true) :
    (clusters rows L).map (fun x => (x.level, x.id)) = (melt rows L).map (fun e => (e.1, e.2.1)) := by
  unfold clusters
  rw [List.map_flatMap]
  apply flatMap_singleton_eq_map
  intro e he
  have hle : ((parentMap rows L).filter (fun p => p.level == e.1 && p.id == e.2.1)).length ≤ 1 := by
    cases hf : (parentMap rows L).filter (fun p => p.level == e.1 && p.id == e.2.1) with
    | nil => simp
    | cons p ps =>
      have hp : p ∈ (parentMap rows L).filter (fun p => p.level == e.1 && p.id == e.2.1) := by simp [hf]
      rw [List.mem_filter] at hp
      obtain ⟨hpm, hpk⟩ := hp
      simp only [Bool.and_eq_true, beq_iff_eq] at hpk
      unfold singleParent at h
      rw [List.all_eq_true] at h
      have := h p hpm
      simp only [decide_eq_true_eq, hpk.1, hpk.2] at this
      rw [hf] at this
      exact this
  generalize hf : (parentMap rows L).filter (fun p => p.level == e.1 && p.id == e.2.1) = ps at hle ⊢
  match ps, hle with
  | [], _ => rfl
  | [_], _ => rfl

theorem clusters_keys_nodup_of_singleParent (rows : List Row) (L : Nat) (h : singleParent rows L = true) :
    ((clusters rows L).map (fun x => (x.level, x.id))).Nodup := by
  rw [clusters_keys_of_singleParent rows L h]
  exact melt_keys_nodup rows L

/-! ## 反例：入れ子でない時 -/

/-- 第 2 層の 0 が、第 1 層の 0 と 1 の両方にまたがると、検査が無ければ同じクラスタ (2, 0) が親違いで 2 回出て、
子の件数（2）が親の件数（1）を超える。今は検査で止まる -/
theorem not_nested_duplicates :
    clusters [[0, 0], [1, 0]] 2 =
      [⟨1, 0, 1, .root⟩, ⟨1, 1, 1, .root⟩, ⟨2, 0, 2, .node 1 0⟩, ⟨2, 0, 2, .node 1 1⟩] := by rfl

theorem not_nested_rejected : singleParent [[0, 0], [1, 0]] 2 = false := by rfl

end KV.Tree
