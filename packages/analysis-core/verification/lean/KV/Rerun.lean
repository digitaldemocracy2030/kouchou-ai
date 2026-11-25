/-
`analysis_core/core/orchestration.py` の `decide_what_to_run`（`build_plan` / `plan_step`）を写したモデル。

コードとの対応
- spec の `step` は `Spec.name`（自然数）、`dependencies.steps` は `Spec.deps`。
- 工程ごとに、コードがファイルや前回の記録から求める値を `Obs` にまとめる:
  `_disabled_reason` が理由を返すか（disabled）、`found_prev`、`artifact_exists`、
  `newer_deps` が空でないか（stale）、`different_params` が空でないか（paramsChanged）。
- `config["only"]` / `config["force"]` / `rerun_reasons` は `Cfg`。
- `plan_step` の if 連鎖の順番はコードと同じ。`changing_deps` は「それまでに組み立てた plan のうち、
  deps に含まれ、run が真のもの」で、コードと同じく plan（＝spec の並びでそれより前の工程）しか見ない。
-/
namespace KV.Rerun

structure Spec where
  name : Nat
  deps : List Nat
deriving Repr, DecidableEq

structure Obs where
  disabled : Bool
  foundPrev : Bool
  artifactExists : Bool
  stale : Bool
  paramsChanged : Bool
deriving Repr, DecidableEq

structure Cfg where
  only : Option Nat := none
  force : Bool := false
  rerun : List Nat := []
deriving Repr, DecidableEq

inductive Reason where
  | disabled | otherOnly | force | thisOnly | rerun | noPrev | noArtifact | depRerun | staleDep | params | nothing
deriving Repr, DecidableEq

structure Item where
  name : Nat
  run : Bool
  reason : Reason
deriving Repr, DecidableEq

def planStep (cfg : Cfg) (obs : Nat → Obs) (plan : List Item) (s : Spec) : Item :=
  let o := obs s.name
  if o.disabled then ⟨s.name, false, .disabled⟩
  else if cfg.only.isSome && cfg.only != some s.name then ⟨s.name, false, .otherOnly⟩
  else if cfg.force then ⟨s.name, true, .force⟩
  else if cfg.only == some s.name then ⟨s.name, true, .thisOnly⟩
  else if cfg.rerun.contains s.name then ⟨s.name, true, .rerun⟩
  else if !o.foundPrev then ⟨s.name, true, .noPrev⟩
  else if !o.artifactExists then ⟨s.name, true, .noArtifact⟩
  else if plan.any (fun x => s.deps.contains x.name && x.run) then ⟨s.name, true, .depRerun⟩
  else if o.stale then ⟨s.name, true, .staleDep⟩
  else if o.paramsChanged then ⟨s.name, true, .params⟩
  else ⟨s.name, false, .nothing⟩

def buildPlan (cfg : Cfg) (obs : Nat → Obs) (specs : List Spec) : List Item :=
  specs.foldl (fun plan s => plan ++ [planStep cfg obs plan s]) []

def runOf (plan : List Item) (n : Nat) : Bool := plan.any (fun x => x.name == n && x.run)

def names (specs : List Spec) : List Nat := specs.map (·.name)

/-- spec の並びが依存順：各工程の deps はすべてそれより前にあり、名前は重複しない -/
inductive Sorted : List Spec → Prop where
  | nil : Sorted []
  | snoc {l s} : Sorted l → (∀ d ∈ s.deps, d ∈ names l) → s.name ∉ names l → Sorted (l ++ [s])

/-- `load_specs` の `validate_specs_order`：各工程がそれより前に並ぶ工程にだけ依存し、名前が重複しない -/
def specsOrderAux : List Nat → List Spec → Bool
  | _, [] => true
  | listed, s :: rest =>
    !listed.contains s.name && s.deps.all (listed.contains ·) && specsOrderAux (listed ++ [s.name]) rest

def specsOrderOk (specs : List Spec) : Bool := specsOrderAux [] specs

/-! ## スキップの健全性のためのモデル

各工程の出力を「設定のうち読むキー（R）」と「deps の出力」の関数とみなす。
無効な工程の出力は none（レポートに入らない）。 -/

abbrev Config := Nat → Nat

def restrict (c : Config) (ks : List Nat) : Config := fun k => if ks.contains k then c k else 0

def compute {V : Type} (F : Nat → Config → List (Option V) → V) (R : Nat → List Nat)
    (dis : Config → Nat → Bool) (c : Config) (specs : List Spec) : Nat → Option V :=
  specs.foldl (fun env s => fun n =>
    if n = s.name then
      (if dis c s.name then none else some (F s.name (restrict c (R s.name)) (s.deps.map env)))
    else env n) (fun _ => none)

/-- 宣言したキー（K）のどれかが前回と違うか（`different_params`） -/
def changed (K : Nat → List Nat) (prev cur : Config) (n : Nat) : Bool :=
  (K n).any (fun k => prev k != cur k)

end KV.Rerun
