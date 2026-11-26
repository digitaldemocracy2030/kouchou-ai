import Lean

open Lean

set_option warningAsError true

namespace ChartSelection

/-- The registry supplies modes that the report enables, in display order.
    A mode can be disabled by the report data or by a viewer setting. -/
structure Mode where
  id : String
  isDisabled : Bool
  deriving ToJson

def availableIds (modes : List Mode) : List String :=
  (modes.filter (!·.isDisabled)).map (·.id)

def choose (available : List String) (requested fallback : Option String) : Option String :=
  if requested.any (· ∈ available) then requested
  else if fallback.any (· ∈ available) then fallback
  else available.head?

def resolve (modes : List Mode) (requested fallback : Option String) : Option String :=
  choose (availableIds modes) requested fallback

theorem resolved_is_available {modes : List Mode} {requested fallback : Option String}
    {id : String} (h : resolve modes requested fallback = some id) :
    ∃ mode ∈ modes, mode.isDisabled = false ∧ mode.id = id := by
  unfold resolve choose at h
  have member : id ∈ availableIds modes := by
    split at h
    next allowed =>
      rw [h] at allowed
      simpa using allowed
    next _ =>
      split at h
      next allowed =>
        rw [h] at allowed
        simpa using allowed
      next _ =>
        exact List.mem_of_head? h
  obtain ⟨mode, present, sameId⟩ := List.mem_map.mp member
  obtain ⟨registered, enabled⟩ := List.mem_filter.mp present
  exact ⟨mode, registered, by simpa using enabled, sameId⟩

theorem keeps_available_request {modes : List Mode} {id : String} {fallback : Option String}
    (h : id ∈ availableIds modes) : resolve modes (some id) fallback = some id := by
  simp [resolve, choose, h]

theorem uses_available_fallback {modes : List Mode} {requested : Option String} {id : String}
    (unavailable : requested.any (· ∈ availableIds modes) = false)
    (h : id ∈ availableIds modes) : resolve modes requested (some id) = some id := by
  simp [resolve, choose, unavailable, h]

theorem uses_first_available {modes : List Mode} {requested fallback : Option String}
    (noRequest : requested.any (· ∈ availableIds modes) = false)
    (noFallback : fallback.any (· ∈ availableIds modes) = false) :
    resolve modes requested fallback = (availableIds modes).head? := by
  simp [resolve, choose, noRequest, noFallback]

theorem no_selection_iff_no_available {modes : List Mode} {requested fallback : Option String} :
    resolve modes requested fallback = none ↔ availableIds modes = [] := by
  constructor
  · intro h
    unfold resolve choose at h
    split at h
    next allowed => simp [h] at allowed
    next _ =>
      split at h
      next allowed => simp [h] at allowed
      next _ => exact List.head?_eq_none_iff.mp h
  · intro h
    cases requested <;> cases fallback <;> simp [resolve, choose, h]

structure Example where
  modes : List Mode
  requested : Option String
  fallback : Option String
  expected : Option String
  deriving ToJson

def examples : List Example :=
  let orders := [[], ["scatterAll"], ["scatterDensity", "treemap", "scatterAll"],
    ["treemap", "scatterAll", "scatterDensity"], ["optional", "treemap"]]
  let requests := [none, some "scatterAll", some "scatterDensity", some "treemap", some "optional", some "removed"]
  let fallbacks := [none, some "scatterAll", some "treemap", some "removed"]
  orders.flatMap fun order =>
    [[], ["scatterAll"], ["scatterDensity", "optional"], order].flatMap fun unavailable =>
      let modes := order.map fun id => Mode.mk id (unavailable.contains id)
      requests.flatMap fun requested =>
        fallbacks.map fun fallback => ⟨modes, requested, fallback, resolve modes requested fallback⟩

end ChartSelection

def main : IO Unit :=
  IO.println (toJson ChartSelection.examples).compress
