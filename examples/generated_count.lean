set_option maxRecDepth 10000
set_option maxHeartbeats 0

def powMod (base exp mod : Nat) : Nat :=
  if mod == 0 then 0
  else if mod == 1 then 0
  else
    let rec loop (b e acc fuel : Nat) : Nat :=
      match fuel with
      | 0 => acc
      | fuel' + 1 =>
          if e == 0 then acc
          else
            let acc' := if e % 2 == 1 then (acc * b) % mod else acc
            loop ((b * b) % mod) (e / 2) acc' fuel'
    loop (base % mod) exp 1 (exp + 1)

def factorial : Nat → Nat
  | 0 => 1
  | n + 1 => (n + 1) * factorial n

def choose (n k : Nat) : Nat :=
  if k > n then 0
  else
    let k := min k (n - k)
    let rec loop (i acc fuel : Nat) : Nat :=
      match fuel with
      | 0 => acc
      | fuel' + 1 =>
          if i >= k then acc
          else loop (i + 1) (acc * (n - i) / (i + 1)) fuel'
    loop 0 1 (k + 1)

def problem_spec (ans : Nat) : Bool := decide (((List.range 99).filter (fun i => let x := i + 1; decide ((((Int.ofNat x) % (3 : Int)) = (0 : Int))))).length = ans)
def f (_n : Nat) : Nat := if problem_spec 33 then 1 else 0

def expected : Array Nat := #[1]

theorem verify :
  (Array.range expected.size).all (fun n => f n == expected[n]!) = true := by
  native_decide
