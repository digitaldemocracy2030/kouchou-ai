import KV.Resolver

namespace KV.Resolver

/-! ## 補題 -/

theorem mem_uniq {x : Nat} : ∀ {l : List Nat}, x ∈ uniq l ↔ x ∈ l
  | [] => by simp [uniq]
  | y :: ys => by
    have ih := @mem_uniq x ys
    by_cases h : x = y <;> simp_all [uniq]

theorem nodup_uniq : ∀ (l : List Nat), (uniq l).Nodup
  | [] => by simp [uniq]
  | y :: ys => by
    rw [uniq, List.nodup_cons]
    exact ⟨by simp, (nodup_uniq ys).filter _⟩

/-- 重複なしで l ⊆ m なら |l| ≤ |m| -/
theorem length_le_of_nodup_subset : ∀ {l m : List Nat}, l.Nodup → (∀ x ∈ l, x ∈ m) → l.length ≤ m.length
  | [], _, _, _ => by simp
  | a :: l, m, hn, hs => by
    rw [List.nodup_cons] at hn
    have ha : a ∈ m := hs a (by simp)
    have : l.length ≤ (m.erase a).length := by
      apply length_le_of_nodup_subset hn.2
      intro x hx
      have hxa : x ≠ a := fun h => hn.1 (h ▸ hx)
      exact (List.mem_erase_of_ne hxa).2 (hs x (by simp [hx]))
    rw [List.length_erase_of_mem ha] at this
    have : 0 < m.length := List.length_pos_of_mem ha
    simp only [List.length_cons]; omega

theorem depsOf_cons (s : Step) (rest : Steps) (w : Nat) (h : s.id ∉ ids rest) :
    depsOf (s :: rest) w = if s.id = w then s.deps else depsOf rest w := by
  unfold depsOf
  simp only [List.reverse_cons, List.find?_append]
  by_cases hw : s.id = w
  · subst hw
    have : rest.reverse.find? (·.id == s.id) = none := by
      rw [List.find?_eq_none]
      intro x hx hxe
      apply h
      simp only [beq_iff_eq] at hxe
      simp only [ids, List.mem_map]
      exact ⟨x, List.mem_reverse.1 hx, hxe⟩
    simp [this]
  · simp [hw]

theorem count_dependents (steps : Steps) (hnd : (ids steps).Nodup) (v w : Nat) :
    (dependents steps v).count w = if w ∈ ids steps then (depsOf steps w).count v else 0 := by
  induction steps with
  | nil => simp [dependents, ids]
  | cons s rest ih =>
    have hnd' : s.id ∉ ids rest ∧ (ids rest).Nodup := List.nodup_cons.1 hnd
    have hmem : w ∈ ids (s :: rest) ↔ w = s.id ∨ w ∈ ids rest := by simp [ids]
    have hdep : dependents (s :: rest) v = List.replicate (s.deps.count v) s.id ++ dependents rest v := by
      simp [dependents]
    rw [hdep, List.count_append, List.count_replicate, ih hnd'.2, depsOf_cons s rest w hnd'.1]
    by_cases hw : s.id = w
    · subst hw; simp [hnd'.1, hmem]
    · have : w ≠ s.id := fun h => hw h.symm
      simp [hw, this, hmem]

theorem mem_dependents {steps : Steps} {v x : Nat} (h : x ∈ dependents steps v) : x ∈ ids steps := by
  simp only [dependents, List.mem_flatMap, List.mem_replicate] at h
  obtain ⟨s, hs, _, rfl⟩ := h
  exact List.mem_map_of_mem hs

/-- まだ並びに入っていない deps の数 -/
def pend (steps : Steps) (order : List Nat) (w : Nat) : Int :=
  ((depsOf steps w).filter (fun d => !order.contains d)).length

theorem filter_len_snoc (o : List Nat) (v : Nat) (hv : v ∉ o) : ∀ (l : List Nat),
    ((l.filter (fun d => !o.contains d)).length : Int) =
      (l.filter (fun d => !(o ++ [v]).contains d)).length + l.count v
  | [] => by simp
  | d :: l => by
    have ih := filter_len_snoc o v hv l
    by_cases hd : d = v
    · subst hd; simp [List.filter_cons, hv, List.count_cons] at ih ⊢; omega
    · by_cases ho : d ∈ o
      · simp [List.filter_cons, ho, List.count_cons, hd] at ih ⊢; omega
      · simp [List.filter_cons, ho, List.count_cons, hd] at ih ⊢; omega

theorem pend_snoc (steps : Steps) (o : List Nat) (v w : Nat) (hv : v ∉ o) :
    pend steps o w = pend steps (o ++ [v]) w + (depsOf steps w).count v := by
  unfold pend; exact filter_len_snoc o v hv _

theorem pend_nonneg (steps : Steps) (o : List Nat) (w : Nat) : 0 ≤ pend steps o w := by
  unfold pend; omega

theorem pend_zero {steps : Steps} {o : List Nat} {w : Nat} (h : pend steps o w = 0) :
    ∀ d ∈ depsOf steps w, d ∈ o := by
  unfold pend at h
  have h' : (depsOf steps w).filter (fun d => !o.contains d) = [] := by
    apply List.eq_nil_of_length_eq_zero; omega
  intro d hd
  rw [List.filter_eq_nil_iff] at h'
  have := h' d hd
  simpa using this

/-! ## relax -/

theorem relax_spec : ∀ (L : List Nat) (indeg : Nat → Int) (q : List Nat),
    (∀ x ∈ L, (L.count x : Int) ≤ indeg x) →
    (∀ x, (relax indeg q L).1 x = indeg x - L.count x) ∧
    (∀ x, x ∈ (relax indeg q L).2 ↔ x ∈ q ∨ (x ∈ L ∧ indeg x = L.count x)) ∧
    (q.Nodup → (∀ x ∈ L, indeg x = L.count x → x ∉ q) → (relax indeg q L).2.Nodup)
  | [], indeg, q, _ => by simp [relax]
  | w :: ws, indeg, q, hpre => by
    let indeg' : Nat → Int := fun x => if x = w then indeg w - 1 else indeg x
    let q' := if indeg w - 1 = 0 then q ++ [w] else q
    have hw : ((w :: ws).count w : Int) ≤ indeg w := hpre w (by simp)
    have hcw : (w :: ws).count w = ws.count w + 1 := by simp [List.count_cons]
    have hpre' : ∀ x ∈ ws, (ws.count x : Int) ≤ indeg' x := by
      intro x hx
      by_cases hxw : x = w
      · subst hxw; simp [indeg']; omega
      · have := hpre x (by simp [hx])
        have hc : (w :: ws).count x = ws.count x := by
          simp [List.count_cons]; intro h; exact absurd h.symm hxw
        simp [indeg', hxw]; omega
    obtain ⟨h1, h2, h3⟩ := relax_spec ws indeg' q' hpre'
    have hrel : relax indeg q (w :: ws) = relax indeg' q' ws := rfl
    rw [hrel]
    refine ⟨?_, ?_, ?_⟩
    · intro x
      rw [h1 x]
      by_cases hxw : x = w
      · subst hxw; simp [indeg', hcw]; omega
      · have hc : (w :: ws).count x = ws.count x := by
          simp [List.count_cons]; intro h; exact absurd h.symm hxw
        simp [indeg', hxw, hc]
    · intro x
      rw [h2 x]
      by_cases hxw : x = w
      · subst hxw
        simp only [indeg', q', if_pos rfl, hcw]
        by_cases hd : indeg x - 1 = 0
        · have hz : ws.count x = 0 := by omega
          have hnot : x ∉ ws := by
            intro hm; have := List.count_pos_iff.2 hm; omega
          simp [hd, hz, hnot]; omega
        · simp [hd]
          constructor
          · rintro (h | ⟨_, h⟩)
            · exact Or.inl h
            · exact Or.inr (by omega)
          · rintro (h | h)
            · exact Or.inl h
            · right
              have hpos : ws.count x ≠ 0 := by omega
              exact ⟨List.count_pos_iff.1 (Nat.pos_of_ne_zero hpos), by omega⟩
      · have hc : (w :: ws).count x = ws.count x := by
          simp [List.count_cons]; intro h; exact absurd h.symm hxw
        simp only [indeg', q', if_neg hxw, hc, List.mem_cons, hxw, false_or]
        split <;> simp [hxw]
    · intro hq hdis
      apply h3
      · simp only [q']
        split
        · rw [List.nodup_append]
          refine ⟨hq, by simp, ?_⟩
          intro a ha b hb
          simp at hb; subst hb
          intro hab; subst hab
          apply hdis a (by simp) _ ha
          omega
        · exact hq
      · intro x hx hxe
        by_cases hxw : x = w
        · subst hxw
          simp only [indeg', if_pos rfl] at hxe
          simp only [q']
          have hpos : 0 < ws.count x := List.count_pos_iff.2 hx
          have hne : ¬ (indeg x - 1 = 0) := by omega
          simp only [hne, if_false]
          exact hdis x (by simp) (by omega)
        · simp only [indeg', if_neg hxw] at hxe
          have hc : (w :: ws).count x = ws.count x := by
            simp [List.count_cons]; intro h; exact absurd h.symm hxw
          simp only [q']
          have hxq : x ∉ q := hdis x (by simp [hx]) (by omega)
          split <;> simp [hxq, hxw]

/-! ## 並びの性質 -/

/-- 末尾に足す時点で、その工程の deps がすべて入っている並び -/
inductive Topo (steps : Steps) : List Nat → Prop where
  | nil : Topo steps []
  | snoc {o v} : Topo steps o → (∀ d ∈ depsOf steps v, d ∈ o) → Topo steps (o ++ [v])

theorem Topo.deps_in {steps : Steps} {o : List Nat} (h : Topo steps o) :
    ∀ x ∈ o, ∀ d ∈ depsOf steps x, d ∈ o := by
  induction h with
  | nil => simp
  | snoc _ hv ih =>
    intro x hx d hd
    simp only [List.mem_append, List.mem_singleton] at hx
    rcases hx with hx | rfl
    · exact List.mem_append_left _ (ih x hx d hd)
    · exact List.mem_append_left _ (hv d hd)

theorem Topo.depsBefore {steps : Steps} {o : List Nat} (h : Topo steps o) : DepsBefore steps o := by
  induction h with
  | nil => intro pre v post he; simp at he
  | @snoc o v _ hv ih =>
    intro pre y post he d hd
    rcases List.append_eq_append_iff.1 he with ⟨a', h1, h2⟩ | ⟨c', h1, h2⟩
    · cases a' with
      | nil => simp at h1 h2; subst h1; obtain ⟨rfl, _⟩ := h2; exact hv d hd
      | cons a as => simp at h2
    · cases c' with
      | nil => simp at h1 h2; subst h1; obtain ⟨rfl, _⟩ := h2; exact hv d hd
      | cons c cs =>
        simp at h2; obtain ⟨rfl, rfl⟩ := h2
        exact ih pre y cs h1 d hd

/-! ## ループの不変条件 -/

structure Inv (steps : Steps) (indeg : Nat → Int) (q order : List Nat) : Prop where
  nodup : (order ++ q).Nodup
  sub : ∀ x ∈ order ++ q, x ∈ ids steps
  indeg : ∀ w ∈ ids steps, indeg w = pend steps order w
  ready : ∀ x ∈ q, ∀ d ∈ depsOf steps x, d ∈ order
  topo : Topo steps order

theorem inv_step (steps : Steps) (hnd : (ids steps).Nodup) (indeg : Nat → Int) (v : Nat) (q order : List Nat)
    (hI : Inv steps indeg (v :: q) order) :
    Inv steps (relax indeg q (dependents steps v)).1 (relax indeg q (dependents steps v)).2 (order ++ [v]) := by
  let L := dependents steps v
  have hnodup := hI.nodup
  rw [List.nodup_append] at hnodup
  obtain ⟨hon, hqn, hdis⟩ := hnodup
  have hvo : v ∉ order := fun h => hdis v h v (by simp) rfl
  have hqn' : q.Nodup := (List.nodup_cons.1 hqn).2
  have hvq : v ∉ q := (List.nodup_cons.1 hqn).1
  have hvids : v ∈ ids steps := hI.sub v (by simp)
  have hvready : ∀ d ∈ depsOf steps v, d ∈ order := hI.ready v (by simp)
  -- L の各要素 x について count x L = count v (depsOf x)
  have hcL : ∀ x ∈ L, L.count x = (depsOf steps x).count v := by
    intro x hx
    rw [count_dependents steps hnd v x, if_pos (mem_dependents hx)]
  have hvdep : ∀ x ∈ L, v ∈ depsOf steps x := by
    intro x hx
    have := List.count_pos_iff.2 hx
    rw [hcL x hx] at this
    exact List.count_pos_iff.1 this
  have hpre : ∀ x ∈ L, (L.count x : Int) ≤ indeg x := by
    intro x hx
    rw [hI.indeg x (mem_dependents hx), pend_snoc steps order v x hvo, hcL x hx]
    have := pend_nonneg steps (order ++ [v]) x
    omega
  obtain ⟨r1, r2, r3⟩ := relax_spec L indeg q hpre
  -- 新しく入る x は order にも v にも q にも無い
  have hnew_not_order : ∀ x ∈ L, x ∉ order := by
    intro x hx hxo
    exact hvo (hI.topo.deps_in x hxo v (hvdep x hx))
  have hnew_ne_v : ∀ x ∈ L, x ≠ v := by
    intro x hx hxv; subst hxv
    exact hvo (hvready x (hvdep x hx))
  have hnew_not_q : ∀ x ∈ L, x ∉ q := by
    intro x hx hxq
    exact hvo (hI.ready x (by simp [hxq]) v (hvdep x hx))
  refine ⟨?_, ?_, ?_, ?_, ?_⟩
  · -- nodup
    rw [List.nodup_append]
    refine ⟨?_, r3 hqn' (fun x hx _ => hnew_not_q x hx), ?_⟩
    · rw [List.nodup_append]; exact ⟨hon, by simp, by
        intro a ha b hb hab; simp at hb; subst hb; subst hab; exact hvo ha⟩
    · intro a ha b hb hab
      subst hab
      rcases (r2 a).1 hb with hq | ⟨hL, _⟩
      · simp only [List.mem_append, List.mem_singleton] at ha
        rcases ha with ha | rfl
        · exact hdis a ha a (by simp [hq]) rfl
        · exact hvq hq
      · simp only [List.mem_append, List.mem_singleton] at ha
        rcases ha with ha | rfl
        · exact hnew_not_order a hL ha
        · exact hnew_ne_v a hL rfl
  · -- sub
    intro x hx
    simp only [List.mem_append, List.mem_singleton] at hx
    rcases hx with (hx | rfl) | hx
    · exact hI.sub x (by simp [hx])
    · exact hvids
    · rcases (r2 x).1 hx with hq | ⟨hL, _⟩
      · exact hI.sub x (by simp [hq])
      · exact mem_dependents hL
  · -- indeg
    intro w hw
    rw [r1 w, hI.indeg w hw, pend_snoc steps order v w hvo, count_dependents steps hnd v w, if_pos hw]
    omega
  · -- ready
    intro x hx d hd
    rcases (r2 x).1 hx with hq | ⟨hL, he⟩
    · exact List.mem_append_left _ (hI.ready x (by simp [hq]) d hd)
    · have hx_ids := mem_dependents hL
      have h0 : pend steps (order ++ [v]) x = 0 := by
        have := hI.indeg x hx_ids
        rw [pend_snoc steps order v x hvo, ← hcL x hL] at this
        omega
      exact pend_zero h0 d hd
  · exact Topo.snoc hI.topo hvready

theorem loop_spec (steps : Steps) (hnd : (ids steps).Nodup) :
    ∀ (n : Nat) (indeg : Nat → Int) (q order : List Nat), Inv steps indeg q order →
      let res := loop steps n indeg q order
      res.Nodup ∧ (∀ x ∈ res, x ∈ ids steps) ∧ Topo steps res
  | 0, indeg, q, order, hI => by
    simp only [loop]
    exact ⟨(List.nodup_append.1 hI.nodup).1, fun x hx => hI.sub x (by simp [hx]), hI.topo⟩
  | n + 1, indeg, [], order, hI => by
    simp only [loop]
    exact ⟨(List.nodup_append.1 hI.nodup).1, fun x hx => hI.sub x (by simp [hx]), hI.topo⟩
  | n + 1, indeg, v :: q, order, hI => by
    simp only [loop]
    exact loop_spec steps hnd n _ _ _ (inv_step steps hnd indeg v q order hI)

theorem inv_init (steps : Steps) : Inv steps (indeg0 steps) (initQueue steps) [] := by
  refine ⟨?_, ?_, ?_, ?_, Topo.nil⟩
  · simp only [List.nil_append, initQueue]; exact (nodup_uniq _).filter _
  · intro x hx
    simp only [List.nil_append, initQueue, List.mem_filter] at hx
    exact mem_uniq.1 hx.1
  · intro w _
    have : (depsOf steps w).filter (fun d => !([] : List Nat).contains d) = depsOf steps w :=
      List.filter_eq_self.mpr (fun _ _ => rfl)
    simp only [indeg0, pend, this]
  · intro x hx d hd
    simp only [initQueue, List.mem_filter, indeg0, beq_iff_eq] at hx
    have : (depsOf steps x).length = 0 := by omega
    rw [List.length_eq_zero_iff] at this
    rw [this] at hd; simp at hd

/-! ## 重複の検出 -/

theorem dupAux_nil : ∀ {seen dups l : List Nat}, dupAux seen dups l = [] →
    dups = [] ∧ (∀ x ∈ l, x ∉ seen) ∧ l.Nodup
  | seen, dups, [], h => by simp [dupAux] at h; simp [h]
  | seen, dups, x :: xs, h => by
    simp only [dupAux] at h
    obtain ⟨h1, h2, h3⟩ := dupAux_nil h
    have hd : dups = [] := by split at h1 <;> simp_all
    subst hd
    have hx : x ∉ seen := by
      intro hm
      simp [hm] at h1
    refine ⟨rfl, ?_, ?_⟩
    · intro y hy
      simp only [List.mem_cons] at hy
      rcases hy with rfl | hy
      · exact hx
      · exact fun hs => h2 y hy (List.mem_cons_of_mem _ hs)
    · exact List.nodup_cons.2 ⟨fun hm => h2 x hm (List.mem_cons_self), h3⟩

/-! ## 主定理 -/

/-- `resolve_execution_order` が並びを返したら、それは全工程をちょうど 1 回ずつ含み、
各工程の depends_on はすべてその工程より前にある（工程 id の重複は先に `DuplicateStepError` で弾かれる） -/
theorem resolve_sound (steps : Steps) (order : List Nat)
    (h : resolve steps = .ok order) :
    order.Nodup ∧ (∀ x, x ∈ order ↔ x ∈ ids steps) ∧ DepsBefore steps order := by
  unfold resolve at h
  split at h
  · simp at h
  rename_i hdup
  have hnd : (ids steps).Nodup := (dupAux_nil (by simpa [dupIds] using hdup)).2.2
  split at h
  · simp at h
  · simp only at h
    split at h
    · simp at h
    · rename_i hlen
      simp only [Except.ok.injEq] at h
      subst h
      obtain ⟨hn, hs, ht⟩ := loop_spec steps hnd (steps.length + 1) _ _ _ (inv_init steps)
      refine ⟨hn, fun x => ⟨hs x, fun hx => ?_⟩, ht.depsBefore⟩
      apply Classical.byContradiction
      intro hxo
      have hle := length_le_of_nodup_subset hn (m := (ids steps).erase x) (by
        intro y hy
        have hyx : y ≠ x := fun e => hxo (e ▸ hy)
        exact (List.mem_erase_of_ne hyx).2 (hs y hy))
      rw [List.length_erase_of_mem hx] at hle
      simp only [bne_iff_ne, ne_eq, Decidable.not_not] at hlen
      have : (ids steps).length = steps.length := by simp [ids]
      have : 0 < (ids steps).length := List.length_pos_of_mem hx
      omega

/-! ## 具体例（コードの振る舞いとして成り立つこと） -/

/-- 存在しない工程への依存は、例外ではなくエラーの一覧に入る -/
theorem validate_lists_missing : validate [⟨0, [5]⟩] = [.missing 0 5] := by rfl

/-- 存在しない依存は、いつでもエラーの一覧に入る -/
theorem validate_reports_missing (steps : Steps) (s : Step) (hs : s ∈ steps) (d : Nat) (hd : d ∈ s.deps)
    (hm : d ∉ ids steps) : Msg.missing s.id d ∈ validate steps := by
  have : Msg.missing s.id d ∈ (dupIds (ids steps)).map Msg.duplicateId ++ steps.flatMap (fun s =>
      (if s.deps.contains s.id then [Msg.selfDep s.id] else []) ++
      (s.deps.filter (fun d => !(ids steps).contains d)).map (fun d => Msg.missing s.id d)) := by
    apply List.mem_append_right
    simp only [List.mem_flatMap, List.mem_append, List.mem_map, List.mem_filter]
    exact ⟨s, hs, Or.inr ⟨d, ⟨hd, by simpa using hm⟩, rfl⟩⟩
  unfold validate
  split <;> simp_all

/-- 工程 id の重複は「循環」ではなく重複として報告される -/
theorem duplicate_id_reported :
    resolve [⟨0, []⟩, ⟨0, []⟩] = .error (.duplicate [0]) ∧
    validate [⟨0, []⟩, ⟨0, []⟩] = [.duplicateId 0] := ⟨rfl, rfl⟩

end KV.Resolver
