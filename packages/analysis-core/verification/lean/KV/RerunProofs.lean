import KV.Rerun

namespace KV.Rerun

/-! ## 補題 -/

theorem buildPlan_snoc (cfg : Cfg) (obs : Nat → Obs) (l : List Spec) (s : Spec) :
    buildPlan cfg obs (l ++ [s]) = buildPlan cfg obs l ++ [planStep cfg obs (buildPlan cfg obs l) s] := by
  simp [buildPlan, List.foldl_append]

theorem planStep_name (cfg : Cfg) (obs : Nat → Obs) (plan : List Item) (s : Spec) :
    (planStep cfg obs plan s).name = s.name := by
  unfold planStep; dsimp only; repeat' split
  all_goals rfl

theorem names_buildPlan (cfg : Cfg) (obs : Nat → Obs) (l : List Spec) :
    (buildPlan cfg obs l).map (·.name) = names l := by
  suffices h : ∀ (init : List Item), (l.foldl (fun plan s => plan ++ [planStep cfg obs plan s]) init).map (·.name)
      = init.map (·.name) ++ names l by simpa [buildPlan] using h []
  induction l with
  | nil => intro init; simp [names]
  | cons s rest ih => intro init; simp [ih, planStep_name, names]

theorem runOf_snoc (p : List Item) (it : Item) (n : Nat) :
    runOf (p ++ [it]) n = (runOf p n || (it.name == n && it.run)) := by
  simp [runOf, List.any_append]

theorem runOf_of_not_mem {p : List Item} {n : Nat} (h : n ∉ p.map (·.name)) : runOf p n = false := by
  simp only [runOf, List.any_eq_false, Bool.and_eq_true, beq_iff_eq, not_and]
  intro x hx hxn
  exact absurd (hxn ▸ List.mem_map_of_mem hx) h

theorem runOf_true {p : List Item} {n : Nat} (h : runOf p n = true) : ∃ x ∈ p, x.name = n ∧ x.run = true := by
  simp only [runOf, List.any_eq_true, Bool.and_eq_true, beq_iff_eq] at h
  exact h

/-- 無効でも -o でもない工程は、deps のどれかが再実行されるなら再実行される -/
theorem planStep_run_of_dep (cfg : Cfg) (obs : Nat → Obs) (plan : List Item) (s : Spec)
    (hd : (obs s.name).disabled = false) (honly : cfg.only = none)
    (hany : plan.any (fun x => s.deps.contains x.name && x.run) = true) :
    (planStep cfg obs plan s).run = true := by
  unfold planStep; dsimp only; repeat' split
  all_goals simp_all

/-- 無効でない工程がスキップされるのは「nothing changed」の時だけで、その時は
deps のどれも再実行されず、宣言したキーも変わっていない -/
theorem planStep_skip (cfg : Cfg) (obs : Nat → Obs) (plan : List Item) (s : Spec)
    (hd : (obs s.name).disabled = false) (honly : cfg.only = none)
    (h : (planStep cfg obs plan s).run = false) :
    plan.any (fun x => s.deps.contains x.name && x.run) = false ∧ (obs s.name).paramsChanged = false := by
  unfold planStep at h; dsimp only at h; repeat' split at h
  all_goals simp_all

theorem Sorted.deps_in {l : List Spec} (h : Sorted l) : ∀ s ∈ l, ∀ d ∈ s.deps, d ∈ names l := by
  induction h with
  | nil => simp
  | @snoc l t _ hdt _ ih =>
    intro s hs d hd
    simp only [List.mem_append, List.mem_singleton] at hs
    have hsub : ∀ x ∈ names l, x ∈ names (l ++ [t]) := by intro x hx; simp [names] at hx ⊢; exact Or.inl hx
    rcases hs with hs | rfl
    · exact hsub _ (ih s hs d hd)
    · exact hsub _ (hdt d hd)

/-- `load_specs` の検査を通った spec は依存順に並んでいる -/
theorem sorted_of_specsOrderOk : ∀ (pre rest : List Spec), Sorted pre →
    specsOrderAux (names pre) rest = true → Sorted (pre ++ rest)
  | pre, [], hs, _ => by simpa using hs
  | pre, s :: rest, hs, h => by
    simp only [specsOrderAux, Bool.and_eq_true, Bool.not_eq_true', List.all_eq_true,
      List.contains_iff_mem] at h
    obtain ⟨⟨hfresh, hdeps⟩, hrest⟩ := h
    have hfresh : s.name ∉ names pre := by simpa using hfresh
    have hs' : Sorted (pre ++ [s]) := Sorted.snoc hs hdeps hfresh
    have hn : names (pre ++ [s]) = names pre ++ [s.name] := by simp [names]
    have := sorted_of_specsOrderOk (pre ++ [s]) rest hs' (by rw [hn]; exact hrest)
    simpa using this

theorem sorted_of_loaded {specs : List Spec} (h : specsOrderOk specs = true) : Sorted specs := by
  simpa using sorted_of_specsOrderOk [] specs Sorted.nil h

/-! ## 主定理 1：再実行は下流へ伝わる -/

/-- spec が依存順に並んでいて -o を使わないなら、再実行される工程の下流は（無効にした工程を除き）
すべて再実行される -/
theorem closure (cfg : Cfg) (honly : cfg.only = none) (obs : Nat → Obs) :
    ∀ (specs : List Spec), Sorted specs →
      ∀ s ∈ specs, ∀ d ∈ s.deps, runOf (buildPlan cfg obs specs) d = true →
        runOf (buildPlan cfg obs specs) s.name = true ∨ (obs s.name).disabled = true := by
  intro specs hs
  induction hs with
  | nil => intro s hs; simp at hs
  | @snoc l t hsorted hdeps hfresh ih =>
    intro s hs d hd hrun
    rw [buildPlan_snoc] at hrun ⊢
    rw [runOf_snoc] at hrun ⊢
    simp only [List.mem_append, List.mem_singleton] at hs
    rcases hs with hs | rfl
    · -- 前からある工程：t の名前は l に無いので、d も s.name も t ではない
      have hsn : s.name ∈ names l := List.mem_map_of_mem hs
      have hst : s.name ≠ t.name := fun e => hfresh (e ▸ hsn)
      rw [planStep_name] at hrun ⊢
      have hrun' : runOf (buildPlan cfg obs l) d = true := by
        have hdl : d ∈ names l := hsorted.deps_in s hs d hd
        have hdt : d ≠ t.name := fun e => hfresh (e ▸ hdl)
        simpa [hdt, Ne.symm hdt] using hrun
      rcases ih s hs d hd hrun' with h | h
      · left; simp [h]
      · right; exact h
    · -- 新しい工程 s：d は l の中にあり、l で再実行される
      have hdl : d ∈ names l := hdeps d hd
      have hdt : d ≠ s.name := fun e => hfresh (e ▸ hdl)
      rw [planStep_name] at hrun
      have hrun' : runOf (buildPlan cfg obs l) d = true := by
        simpa [hdt, Ne.symm hdt] using hrun
      by_cases hdis : (obs s.name).disabled = true
      · right; exact hdis
      · left
        have hdis' : (obs s.name).disabled = false := by simpa using hdis
        have hany : (buildPlan cfg obs l).any (fun x => s.deps.contains x.name && x.run) = true := by
          obtain ⟨x, hx, hxn, hxr⟩ := runOf_true hrun'
          simp only [List.any_eq_true, Bool.and_eq_true, List.contains_iff_mem]
          exact ⟨x, hx, hxn ▸ hd, hxr⟩
        have := planStep_run_of_dep cfg obs _ s hdis' honly hany
        simp [this, planStep_name]

/-- `load_specs` の検査を通った spec なら、-o を使わない限り、再実行は下流へ伝わる -/
theorem closure_of_loaded (cfg : Cfg) (honly : cfg.only = none) (obs : Nat → Obs) (specs : List Spec)
    (h : specsOrderOk specs = true) :
    ∀ s ∈ specs, ∀ d ∈ s.deps, runOf (buildPlan cfg obs specs) d = true →
      runOf (buildPlan cfg obs specs) s.name = true ∨ (obs s.name).disabled = true :=
  closure cfg honly obs specs (sorted_of_loaded h)

/-- 依存順でない spec は `load_specs` で弾かれる -/
theorem unsorted_rejected : specsOrderOk [⟨1, [0]⟩, ⟨0, []⟩] = false := by rfl

/-! ## 主定理 2：スキップしても結果は変わらない -/

/-- 前回と今回の設定から `decide_what_to_run` が見る値。foundPrev / artifactExists / stale は任意 -/
def obsOf (dis : Config → Nat → Bool) (K : Nat → List Nat) (prev cur : Config) (fp ae st : Nat → Bool) :
    Nat → Obs :=
  fun n => ⟨dis cur n, fp n, ae n, st n, changed K prev cur n⟩

section Sound
variable {V : Type} (F : Nat → Config → List (Option V) → V) (R : Nat → List Nat) (dis : Config → Nat → Bool)

theorem compute_snoc (c : Config) (l : List Spec) (s : Spec) (n : Nat) :
    compute F R dis c (l ++ [s]) n =
      if n = s.name then
        (if dis c s.name then none else some (F s.name (restrict c (R s.name)) (s.deps.map (compute F R dis c l))))
      else compute F R dis c l n := by
  simp only [compute, List.foldl_append, List.foldl_cons, List.foldl_nil]

theorem compute_dis (c : Config) {l : List Spec} (hs : Sorted l) :
    ∀ n ∈ names l, dis c n = true → compute F R dis c l n = none := by
  induction hs with
  | nil => intro n hn; simp [names] at hn
  | @snoc l t _ _ _ ih =>
    intro n hn hd
    rw [compute_snoc]
    by_cases hnt : n = t.name
    · subst hnt; simp [hd]
    · rw [if_neg hnt]
      apply ih n _ hd
      simp [names] at hn ⊢
      rcases hn with ⟨a, ha, rfl⟩ | h
      · exact ⟨a, ha, rfl⟩
      · exact absurd h hnt

/-- spec が依存順で、-o を使わず、
(hR) 各工程が実際に読む設定キーは、再実行の判定に使うキー（params・global_params・LLM なら prompt / model）に含まれ、
(hD) 各工程とその deps が無効かどうかは、その工程の判定キーだけで決まる
なら、無効でない工程がスキップされた時、その出力は今回の設定で計算し直したものと一致する -/
theorem skip_sound (cfg : Cfg) (honly : cfg.only = none) (K : Nat → List Nat) (prev cur : Config)
    (fp ae st : Nat → Bool) (hR : ∀ n, ∀ k ∈ R n, k ∈ K n) :
    ∀ (specs : List Spec), Sorted specs →
      (∀ s ∈ specs, ∀ d, (d ∈ s.deps ∨ d = s.name) → (∀ k ∈ K s.name, prev k = cur k) → dis prev d = dis cur d) →
      ∀ s ∈ specs, runOf (buildPlan cfg (obsOf dis K prev cur fp ae st) specs) s.name = false →
        dis cur s.name = false →
        compute F R dis cur specs s.name = compute F R dis prev specs s.name := by
  intro specs hs
  induction hs with
  | nil => intro _ s hs; simp at hs
  | @snoc l t hsorted hdeps hfresh ih =>
    intro hD s hs hrun hdis
    have hD' : ∀ s ∈ l, ∀ d, (d ∈ s.deps ∨ d = s.name) → (∀ k ∈ K s.name, prev k = cur k) →
        dis prev d = dis cur d := fun s hs => hD s (List.mem_append_left _ hs)
    rw [buildPlan_snoc, runOf_snoc, planStep_name] at hrun
    rw [compute_snoc, compute_snoc]
    simp only [List.mem_append, List.mem_singleton] at hs
    rcases hs with hs | rfl
    · have hsn : s.name ∈ names l := List.mem_map_of_mem hs
      have hst : s.name ≠ t.name := fun e => hfresh (e ▸ hsn)
      rw [if_neg hst, if_neg hst]
      have : runOf (buildPlan cfg (obsOf dis K prev cur fp ae st) l) s.name = false := by
        simpa [Ne.symm hst] using hrun
      exact ih hD' s hs this hdis
    · rw [if_pos rfl, if_pos rfl]
      have hnot : s.name ∉ (buildPlan cfg (obsOf dis K prev cur fp ae st) l).map (·.name) := by
        rw [names_buildPlan]; exact hfresh
      rw [runOf_of_not_mem hnot, Bool.false_or] at hrun
      have hrun' : (planStep cfg (obsOf dis K prev cur fp ae st)
          (buildPlan cfg (obsOf dis K prev cur fp ae st) l) s).run = false := by
        simpa using hrun
      obtain ⟨hany, hpc⟩ := planStep_skip cfg _ _ s hdis honly hrun'
      have hK : ∀ k ∈ K s.name, prev k = cur k := by
        simp only [obsOf, changed, List.any_eq_false, bne_iff_ne, ne_eq, Decidable.not_not] at hpc
        exact hpc
      have hdisp : dis prev s.name = false := by rw [hD s (by simp) s.name (Or.inr rfl) hK]; exact hdis
      simp only [hdis, hdisp, Bool.false_eq_true, if_false]
      have hrest : restrict cur (R s.name) = restrict prev (R s.name) := by
        funext k
        simp only [restrict]
        split
        · rename_i hk
          exact (hK k (hR _ k (by simpa using hk))).symm
        · rfl
      have hmap : s.deps.map (compute F R dis cur l) = s.deps.map (compute F R dis prev l) := by
        apply List.map_congr_left
        intro d hd
        have hdl : d ∈ names l := hdeps d hd
        have hdrun : runOf (buildPlan cfg (obsOf dis K prev cur fp ae st) l) d = false := by
          cases h : runOf (buildPlan cfg (obsOf dis K prev cur fp ae st) l) d
          · rfl
          · obtain ⟨x, hx, hxn, hxr⟩ := runOf_true h
            have : (buildPlan cfg (obsOf dis K prev cur fp ae st) l).any
                (fun x => s.deps.contains x.name && x.run) = true := by
              simp only [List.any_eq_true, Bool.and_eq_true, List.contains_iff_mem]
              exact ⟨x, hx, hxn ▸ hd, hxr⟩
            rw [hany] at this; exact absurd this (by simp)
        have hdd := hD s (by simp) d (Or.inl hd) hK
        cases hdc : dis cur d
        · obtain ⟨sd, hsd, rfl⟩ := List.mem_map.1 hdl
          exact ih hD' sd hsd hdrun hdc
        · rw [hdc] at hdd
          rw [compute_dis F R dis cur hsorted d hdl hdc, compute_dis F R dis prev hsorted d hdl hdd]
      rw [hrest, hmap]

end Sound

/-! ## 反例 -/

/-- spec が依存順でないと、上流（0）が再実行されても下流（1）はスキップされる（だから `load_specs` で検査する） -/
theorem unsorted_breaks_closure :
    let obs : Nat → Obs := fun n =>
      if n = 0 then ⟨false, true, true, false, true⟩ else ⟨false, true, true, false, false⟩
    runOf (buildPlan {} obs [⟨1, [0]⟩, ⟨0, []⟩]) 0 = true ∧
    runOf (buildPlan {} obs [⟨1, [0]⟩, ⟨0, []⟩]) 1 = false := ⟨rfl, rfl⟩

/-! 意見分類（工程 0、キー 0 = `opinion_classification.enabled`）と集計（工程 1）だけを取り出した例。
集計は「分類が有効なら分類を混ぜる」（`hierarchical_aggregation.py` の `if config.get("opinion_classification", {}).get("enabled")`）
ので、キー 0 を読む。このキーを判定に入れないと、無効に戻した時に古い分類が残る。
今の spec は集計の `global_params` に `opinion_classification.enabled` を入れている（#1227）。 -/

def exSpecs : List Spec := [⟨0, []⟩, ⟨1, [0]⟩]
def exDis (c : Config) (n : Nat) : Bool := n == 0 && c 0 == 0
def exF : Nat → Config → List (Option Nat) → Nat
  | 1, c, [some v] => if c 0 == 1 then v + 1 else 0
  | 1, _, _ => 0
  | _, _, _ => 7
def exR : Nat → List Nat
  | 1 => [0]
  | _ => []
/-- #1227 より前の spec：分類はキー 0 を宣言しているが、集計は宣言していない -/
def exK : Nat → List Nat
  | 0 => [0]
  | _ => []
/-- 集計もキー 0 を宣言した場合（今の spec） -/
def exKfixed : Nat → List Nat := fun _ => [0]
def exPrev : Config := fun _ => 1
def exCur : Config := fun _ => 0
def exObs (K : Nat → List Nat) : Nat → Obs := obsOf exDis K exPrev exCur (fun _ => true) (fun _ => true) (fun _ => false)

/-- 前回は分類を有効にして完了し、今回は無効にした。集計はスキップされるが、
今の設定で計算し直すと結果が変わる（前回は分類を混ぜた 8、今回なら 0） -/
theorem disable_optin_keeps_stale_output :
    runOf (buildPlan {} (exObs exK) exSpecs) 1 = false ∧
    compute exF exR exDis exPrev exSpecs 1 = some 8 ∧
    compute exF exR exDis exCur exSpecs 1 = some 0 := ⟨rfl, rfl, rfl⟩

/-- 集計がキー 0 を判定に含めれば、再実行される -/
theorem declaring_enabled_reruns : runOf (buildPlan {} (exObs exKfixed) exSpecs) 1 = true := rfl

/-- この例は skip_sound の前提 hR（集計はキー 0 を読むのに宣言していない）を破っている -/
theorem example_violates_hR : ¬ (∀ n, ∀ k ∈ exR n, k ∈ exK n) := by
  intro h; have := h 1 0 (by simp [exR]); simp [exK] at this

end KV.Rerun
