
NURSE ROSTERING

1. MODELLING

The roster is a table X[i][d] with values in {M, A, E, R, B}. Instead of
treating every cell as an independent CSP variable, one whole day is treated
as a single compound decision: the set of nurses put on B, M, A and E on that
day. A day is only ever committed if it already meets the exact cover
(count(M)+count(B)=m, count(A)+count(B)=a, count(E)=e, count(B)=0 on general
days, count(B)>=1 on surgical days). Consequently H4 and H7 are satisfied by
construction and never have to be searched over or repaired. The remaining
constraints are per nurse and become domain filters for that day:

  H9 / K budget / H5 : nurse i is available today iff it is not on leave,
                       used[i] < K, and streak[i] < 5, where used counts
                       consumed shifts (B counts 2) and streak counts
                       consecutive working days. "streak >= 5 forces R" is
                       exactly equivalent to "every 6-day window has an R".
  H2, H3, H6         : the shift of yesterday restricts today's domain -
                       after M or E: no M/B; after B: only R or E.
  H1                 : B only for nurses with index < N_s, and only on S days.

2. PART A - CONSTRUCTIVE SEARCH WITH LOOKAHEAD

Days are assigned left to right. For day d the algorithm computes the domains
above, chooses the number of surgical shifts b (the minimum feasible value,
b >= max(1, m+a+e-|available|) on an S day), and then fills B, M, A and E in
that order - most constrained shift first, because only nurses that rested or
worked an afternoon yesterday can take a morning.

Value ordering inside each shift uses three heuristics:

 (a) Urgency. Nurses are ranked by (K - used[i]) - rate * (remaining non-leave
     days of i), where rate = (m+a+e)/N. This prefers a nurse whose K budget
     would otherwise expire unused - it both balances the load when K is loose
     and prevents wasted capacity when K is tight or when a nurse has many
     upcoming leave days.
 (b) Surgical reservation. If the surgical nurses' remaining B capacity,
     sum over i < N_s of floor((K-used[i])/2), is not comfortably larger than
     the number of surgical days still to come, surgical nurses are penalised
     (or forbidden) for ordinary M/A/E work, so that H7 stays satisfiable.
 (c) Evening preference. A nurse on E tonight cannot take a morning tomorrow,
     so E is preferentially given to nurses who are unusable tomorrow anyway
     (on leave, or out of budget).

After a day is committed, a one step lookahead rejects it if tomorrow would
have fewer than m morning-capable nurses, or fewer available nurses than the
cover needs, or - on a surgical day - no surgical nurse able to take B. This
single check removes the large majority of dead ends.

Failures trigger chronological backtracking (a bounded number of randomised
re-tries per day, then a step back to the previous day) under a global node
budget; when the budget is exhausted the whole construction restarts with a
fresh random seed until the time budget T runs out. If no roster is found,
the empty object {} is written.

On randomly generated instances that pass a set of necessary feasibility
conditions, this finds a valid roster for 136 of 138 instances, typically in
about 25 ms for N = 50, D = 30.

3. PART B - SIMULATED ANNEALING ON THE SOFT CONSTRAINT

The objective decomposes per nurse as
        cost(i) = 3*(C_iM^2 + C_iA^2 + C_iE^2) - (C_iM + C_iA + C_iE)^2 ,
so any local change only needs the counts of the nurses it touches.

Phase 1 runs several constructions, with the marginal increase of cost(i)
added as a tie breaker in the value ordering, and keeps the cheapest valid
roster. It is written to disk immediately, so a valid answer always exists
even if the process is stopped.

Phase 2 improves it by simulated annealing with two neighbourhood moves:

  Move 1 (swap): pick a day d and two nurses i, j and exchange their shifts on
  that day. Exchanging shifts within a column cannot change any daily count,
  so H4 and H7 hold automatically; only the nurse local constraints (leave,
  B legality, the day-pair rules with d-1 and d+1, the 6-day rest windows and
  the K budget) are re-checked, in O(1). The cost delta involves two nurses.

  Move 2 (split / merge): on a surgical day turn a B into an M for that nurse
  plus an A for a resting nurse, or the reverse. This keeps M+B and A+B fixed
  and so preserves the cover, while allowing the number of B shifts per day to
  change after construction - something Move 1 alone cannot do.

The temperature is annealed geometrically as a function of elapsed wall-clock
time, so the schedule adapts to the budget T; the incumbent best is kept and
the annealer is restarted from it in successive slices (a reheat).

Stopping criterion. The objective is convex and the column sums of the counts
table are fixed at (mD, aD, eD), so by Jensen's inequality
        C >= N * f(mD/N, aD/N, eD/N),
and since C is an integer this bound may be rounded up. The search stops as
soon as the incumbent reaches it, which certifies optimality on many instances
and saves the remaining budget.

4. RESULTS

Measured against a Lagrangian lower bound of the same relaxation (fixed column
sums, all scheduling constraints dropped):

  N=10 D=14 : construction 52  -> annealed 44  (bound 44)
  N=20 D=20 : construction 130 -> annealed 120 (bound 120)
  N=50 D=30 : construction 510 -> annealed 460 (bound 460)
  N=30 D=30 : annealed 184 (bound 180)
  N=50 D=30 : construction 886 -> annealed 700 (bound 700)

Four of the five are provably optimal. All outputs were checked with the
supplied verifier, and over a separate 40-instance randomised run the
annealer never produced an invalid roster.
