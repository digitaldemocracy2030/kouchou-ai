import KV.Resolver
/-
全数検査：工程が n 個以下（自己依存を含むすべての依存グラフ）で、
`resolve` が並びを返す ⇔ 依存を守る並び（トポロジカル順）が存在する、を確かめる。
証明したのは「返した並びは正しい」（`resolve_sound`）の向きだけなので、逆向き（循環が無ければ必ず返す）をここで見る。
-/
namespace KV.Check
open KV.Resolver

def insertAll (x : Nat) : List Nat → List (List Nat)
  | [] => [[x]]
  | y :: ys => (x :: y :: ys) :: (insertAll x ys).map (y :: ·)

def perms : List Nat → List (List Nat)
  | [] => [[]]
  | x :: xs => (perms xs).flatMap (insertAll x)

def depsBeforeB (steps : Steps) (order : List Nat) : Bool :=
  (List.range order.length).all (fun i =>
    (depsOf steps (order.getD i 0)).all (fun d => (order.take i).contains d))

def graph (n mask : Nat) : Steps :=
  (List.range n).map (fun i => ⟨i, (List.range n).filter (fun j => (mask >>> (i * n + j)) % 2 == 1)⟩)

def run (maxN : Nat) : IO UInt32 := do
  let mut bad := 0
  for n in List.range (maxN + 1) do
    let mut total := 0
    let mut acyclic := 0
    for mask in List.range (2 ^ (n * n)) do
      let steps := graph n mask
      let ok := match resolve steps with | .ok _ => true | .error _ => false
      let hasTopo := (perms (List.range n)).any (depsBeforeB steps)
      total := total + 1
      if hasTopo then acyclic := acyclic + 1
      if ok != hasTopo then
        bad := bad + 1
        IO.println s!"mismatch n={n} mask={mask}"
    IO.println s!"n={n}: graphs={total} acyclic={acyclic}"
  IO.println s!"mismatches={bad}"
  return (if bad == 0 then 0 else 1)

end KV.Check
