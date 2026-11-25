/-
`analysis_core/workflow/resolver.py` の `resolve_execution_order` と `validate_dependencies` を写したモデル。

コードとの対応
- 工程の id は自然数。`WorkflowStep.depends_on` は `Step.deps`。
- `in_degree` は `Nat → Int`（Python の int は負になりうるので Int にする。Nat だと 0 - 1 = 0 になり、
  `== 0` の判定がコードとずれる）。
- `dependents[dep].append(step.id)` は、工程の並び順に、`deps` に dep が現れる回数だけ step.id を足す。
- `deque` の popleft / append は、リストの先頭を取る / 末尾に足す。
- `in_degree[step.id] = len(step.depends_on)` は後から書いた方が勝つので、`depsOf` は逆順の find? で引く。
-/
namespace KV.Resolver

structure Step where
  id : Nat
  deps : List Nat
deriving Repr, DecidableEq

abbrev Steps := List Step

def ids (steps : Steps) : List Nat := steps.map (·.id)

/-- `in_degree[v]` の初期値の元になる deps（同じ id が複数あれば最後のもの）。 -/
def depsOf (steps : Steps) (v : Nat) : List Nat :=
  match steps.reverse.find? (·.id == v) with
  | some s => s.deps
  | none => []

/-- `dependents[v]` -/
def dependents (steps : Steps) (v : Nat) : List Nat :=
  steps.flatMap (fun s => List.replicate (s.deps.count v) s.id)

/-- 先に出たものを残して重複を除く（dict のキーの順） -/
def uniq : List Nat → List Nat
  | [] => []
  | x :: xs => x :: (uniq xs).filter (· != x)

def indeg0 (steps : Steps) (v : Nat) : Int := (depsOf steps v).length

def initQueue (steps : Steps) : List Nat :=
  (uniq (ids steps)).filter (fun v => indeg0 steps v == 0)

/-- `for dependent_id in dependents[current]: in_degree -= 1; if == 0: queue.append` -/
def relax (indeg : Nat → Int) (q : List Nat) : List Nat → (Nat → Int) × List Nat
  | [] => (indeg, q)
  | w :: ws =>
    let d := indeg w - 1
    let indeg' := fun x => if x = w then d else indeg x
    relax indeg' (if d = 0 then q ++ [w] else q) ws

/-- `while queue:` を燃料つきで。燃料は工程数 + 1 渡す（`Check.lean` と差分テストで尽きないことを確かめる）。 -/
def loop (steps : Steps) : Nat → (Nat → Int) → List Nat → List Nat → List Nat
  | 0, _, _, order => order
  | _ + 1, _, [], order => order
  | n + 1, indeg, v :: q, order =>
    let r := relax indeg q (dependents steps v)
    loop steps n r.1 r.2 (order ++ [v])

inductive Err where
  | duplicate (ids : List Nat)
  | missing (step dep : Nat)
  | cyclic (unprocessed : List Nat)
deriving Repr, DecidableEq

/-- `_duplicate_ids`：2 回目に出た id を、最初に重複した順に 1 回ずつ -/
def dupAux : List Nat → List Nat → List Nat → List Nat
  | _, dups, [] => dups
  | seen, dups, x :: xs => dupAux (x :: seen) (if seen.contains x && !dups.contains x then dups ++ [x] else dups) xs

def dupIds (l : List Nat) : List Nat := dupAux [] [] l

/-- 最初に見つかる存在しない依存（工程順、deps 順） -/
def firstMissing (steps : Steps) : Option (Nat × Nat) :=
  steps.findSome? (fun s => (s.deps.find? (fun d => !(ids steps).contains d)).map (fun d => (s.id, d)))

def resolve (steps : Steps) : Except Err (List Nat) :=
  if !(dupIds (ids steps)).isEmpty then .error (.duplicate (dupIds (ids steps))) else
  match firstMissing steps with
  | some (s, d) => .error (.missing s d)
  | none =>
    let order := loop steps (steps.length + 1) (indeg0 steps) (initQueue steps) []
    if order.length != steps.length then
      .error (.cyclic ((ids steps).filter (fun v => !order.contains v)))
    else .ok order

inductive Msg where
  | duplicateId (id : Nat)
  | selfDep (step : Nat)
  | missing (step dep : Nat)
  | cyclic (unprocessed : List Nat)
deriving Repr, DecidableEq

/-- `validate_dependencies`。例外は投げず、エラーの一覧を返す（重複と存在しない依存は先に一覧に入るので、
`resolve` の `DuplicateStepError` / `MissingDependencyError` は捨てる） -/
def validate (steps : Steps) : List Msg :=
  let errs := (dupIds (ids steps)).map Msg.duplicateId ++ steps.flatMap (fun s =>
    (if s.deps.contains s.id then [Msg.selfDep s.id] else []) ++
    (s.deps.filter (fun d => !(ids steps).contains d)).map (fun d => Msg.missing s.id d))
  match resolve steps with
  | .error (.cyclic u) => errs ++ [Msg.cyclic u]
  | _ => errs

/-! ## 仕様 -/

/-- 並び `order` の中で、各工程の deps がすべてその工程より前にある -/
def DepsBefore (steps : Steps) (order : List Nat) : Prop :=
  ∀ pre v post, order = pre ++ v :: post → ∀ d ∈ depsOf steps v, d ∈ pre

end KV.Resolver
