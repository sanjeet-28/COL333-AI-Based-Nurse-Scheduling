import csv
import json
import random
import sys
import time

START_TIME = time.time()

LOAD = {'M': 1, 'A': 1, 'E': 1, 'B': 2, 'R': 0}


def parse_input(input_csv):
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)
        N = int(row['N'])
        D = int(row['D'])
        N_s = int(row['N_s'])
        N_g = int(row['N_g'])
        m = int(row['m'])
        a = int(row['a'])
        e = int(row['e'])
        T = float(row['T'])
        days = row['days']
        max_shifts = int(row['K'])
        leaves = row['leaves']
    return N, D, N_s, N_g, m, a, e, T, days, max_shifts, leaves


def nurse_cost(x, y, z):
    t = x + y + z
    return 3 * (x * x + y * y + z * z) - t * t


def pair_ok(prev, cur):
    if prev == 'B':
        return cur == 'R' or cur == 'E'
    if prev == 'M' or prev == 'E':
        return cur != 'M' and cur != 'B'
    return True


class Problem:
    def __init__(self, path):
        (self.N, self.D, self.Ns, self.Ng, self.m, self.a, self.e,
         self.T, self.days, self.K, leaves) = parse_input(path)
        N, D = self.N, self.D
        self.leave = [[leaves[i * D + d] == 'L' for d in range(D)]
                      for i in range(N)]
        self.need = self.m + self.a + self.e          
        self.is_S = [c == 'S' for c in self.days]
        self.avail_after = []
        for i in range(N):
            suf = [0] * (D + 1)
            for d in range(D - 1, -1, -1):
                suf[d] = suf[d + 1] + (0 if self.leave[i][d] else 1)
            self.avail_after.append(suf)
        self.rate = self.need / float(N) if N else 0.0
        self.s_after = [0] * (D + 1)
        for d in range(D - 1, -1, -1):
            self.s_after[d] = self.s_after[d + 1] + (1 if self.is_S[d] else 0)

class Builder:

    def __init__(self, P, rng):
        self.P = P
        self.rng = rng
        N = P.N
        self.grid = [['R'] * P.D for _ in range(N)]
        self.cM = [0] * N
        self.cA = [0] * N
        self.cE = [0] * N
        self.used = [0] * N      
        self.last = ['R'] * N     
        self.streak = [0] * N     

    def snapshot(self):
        return (self.cM[:], self.cA[:], self.cE[:], self.used[:],
                self.last[:], self.streak[:])

    def restore(self, s):
        self.cM, self.cA, self.cE, self.used, self.last, self.streak = (
            s[0][:], s[1][:], s[2][:], s[3][:], s[4][:], s[5][:])

    def marginal(self, i, shift):
        x, y, z = self.cM[i], self.cA[i], self.cE[i]
        s = x + y + z
        if shift == 'M':
            return 6 * x - 2 * s + 2
        if shift == 'A':
            return 6 * y - 2 * s + 2
        if shift == 'E':
            return 6 * z - 2 * s + 2
        return 6 * x + 6 * y - 4 * s + 2          

    def assign_day(self, d, w_cost):
        P, rng = self.P, self.rng
        N, K = P.N, P.K
        leave, used, last, streak = P.leave, self.used, self.last, self.streak


        avail = []
        for i in range(N):
            if leave[i][d] or used[i] >= K or streak[i] >= 5:
                continue
            avail.append(i)
        if len(avail) < P.need - min(P.m, P.a):
            return False

        can_m = [i for i in avail if last[i] == 'A' or last[i] == 'R']
        can_a = [i for i in avail if last[i] != 'B']
        if len(can_m) < P.m:                      
            return False

        if P.is_S[d]:
            can_b = [i for i in can_m if i < P.Ns and used[i] + 2 <= K]
            b_lo = max(1, P.need - len(avail))
            b_hi = min(P.m, P.a, len(can_b))
        else:
            can_b = []
            b_lo = b_hi = 0
            if len(avail) < P.need:
                return False
        if b_lo > b_hi:
            return False
        b = b_lo if (b_lo == b_hi or rng.random() < 0.8) else rng.randint(b_lo, b_hi)

        if len(can_a) < P.m + P.a - b or len(avail) < P.need - b:
            return False

        taken = set()

        rate = P.rate
        av_after = P.avail_after
        future_S = P.s_after[d + 1] if d + 1 <= P.D else 0
        b_cap = 0
        for i in range(P.Ns):
            r = K - used[i]
            if r > 0:
                b_cap += r // 2
        b_slack = b_cap - future_S

        def choose(pool, k, shift):
            if k <= 0:
                return []
            scored = []
            for i in pool:
                if i in taken:
                    continue
                if shift != 'B' and i < P.Ns:
                    loss = 1 if (K - used[i]) % 2 == 0 else 0
                    if loss:
                        if b_slack <= 0:
                            continue          
                        sc0 = 400.0 / b_slack
                    else:
                        sc0 = 0.0
                else:
                    sc0 = 0.0
                urgency = (K - used[i]) - rate * av_after[i][d + 1]
                sc = sc0 - 100.0 * urgency + 20.0 * streak[i]
                sc += w_cost * self.marginal(i, shift)
                if shift == 'E' and d + 1 < P.D:
                    if not leave[i][d + 1] and used[i] + 1 < K:
                        sc += 30.0
                sc += rng.random() * 40.0
                scored.append((sc, i))
            if len(scored) < k:
                return None
            scored.sort()
            return [i for _, i in scored[:k]]

        plan = []
        for pool, k, shift in ((can_b, b, 'B'), (can_m, P.m - b, 'M'),
                               (can_a, P.a - b, 'A'), (avail, P.e, 'E')):
            picked = choose(pool, k, shift)
            if picked is None:
                return False
            taken.update(picked)
            plan.append((picked, shift))

        
        for picked, shift in plan:
            for i in picked:
                self.grid[i][d] = shift
                if shift == 'B':
                    self.cM[i] += 1
                    self.cA[i] += 1
                elif shift == 'M':
                    self.cM[i] += 1
                elif shift == 'A':
                    self.cA[i] += 1
                else:
                    self.cE[i] += 1
                used[i] += LOAD[shift]
                last[i] = shift
                streak[i] += 1
        for i in range(N):
            if i not in taken:
                self.grid[i][d] = 'R'
                last[i] = 'R'
                streak[i] = 0

        if d + 1 < P.D:
            nxt = d + 1
            free = 0
            morning_ready = 0
            for i in range(N):
                if leave[i][nxt] or used[i] >= K or streak[i] >= 5:
                    continue
                free += 1
                if last[i] == 'A' or last[i] == 'R':
                    morning_ready += 1
            if morning_ready < P.m:
                return False
            slack = min(P.m, P.a) if P.is_S[nxt] else 0
            if free < P.need - slack:
                return False
            if P.is_S[nxt]:
                for i in range(P.Ns):
                    if (not leave[i][nxt] and used[i] + 2 <= K
                            and streak[i] < 5
                            and (last[i] == 'A' or last[i] == 'R')):
                        break
                else:
                    return False
        return True


def construct(P, rng, w_cost, deadline):
    B = Builder(P, rng)
    snaps = [None] * (P.D + 1)
    tries = [0] * (P.D + 1)
    max_tries = 8
    budget = 60 * P.D + 500          
    d = 0
    while d < P.D:
        budget -= 1
        if budget <= 0:
            return None
        if (budget & 63) == 0 and time.time() > deadline:
            return None
        if snaps[d] is None:
            snaps[d] = B.snapshot()
            tries[d] = 0
        if tries[d] >= max_tries:            
            snaps[d] = None
            d -= 1
            if d < 0:
                return None
            tries[d] += 1
            continue
        tries[d] += 1
        B.restore(snaps[d])
        if B.assign_day(d, w_cost):
            d += 1
    return B.grid

def counts_of(P, grid):
    cM = [0] * P.N
    cA = [0] * P.N
    cE = [0] * P.N
    used = [0] * P.N
    for i in range(P.N):
        row = grid[i]
        for d in range(P.D):
            s = row[d]
            if s == 'M':
                cM[i] += 1
            elif s == 'A':
                cA[i] += 1
            elif s == 'E':
                cE[i] += 1
            elif s == 'B':
                cM[i] += 1
                cA[i] += 1
            used[i] += LOAD[s]
    return cM, cA, cE, used


def total_cost(P, grid):
    cM, cA, cE, _ = counts_of(P, grid)
    return sum(nurse_cost(cM[i], cA[i], cE[i]) for i in range(P.N))


def rest_ok(row, d, D):
    if D < 6:
        return True
    lo = d - 5
    if lo < 0:
        lo = 0
    hi = d if d < D - 6 else D - 6
    for start in range(lo, hi + 1):
        blocked = True
        for t in range(start, start + 6):
            if row[t] == 'R':
                blocked = False
                break
        if blocked:
            return False
    return True


def lower_bound(P):
    if P.N == 0:
        return 0
    M, A, E = P.m * P.D, P.a * P.D, P.e * P.D
    num = 3 * (M * M + A * A + E * E) - (M + A + E) ** 2
    return -((-num) // P.N)


def anneal(P, grid, deadline, rng, floor_cost=None):
    N, D, Ns, K = P.N, P.D, P.Ns, P.K
    leave = P.leave
    cM, cA, cE, used = counts_of(P, grid)
    cost = sum(nurse_cost(cM[i], cA[i], cE[i]) for i in range(N))

    best = [row[:] for row in grid]
    best_cost = cost
    s_days = [d for d in range(D) if P.is_S[d]]

    t_start = time.time()
    span = max(deadline - t_start, 0.01)
    T0, T1 = max(4.0, cost / (4.0 * N + 1.0)), 0.08
    temp = T0
    it = 0

    def fits(i, d, s):
        """nurse level legality of putting shift s on nurse i, day d."""
        if s != 'R' and leave[i][d]:
            return False
        if s == 'B' and (i >= Ns or not P.is_S[d]):
            return False
        if d > 0 and not pair_ok(grid[i][d - 1], s):
            return False
        if d + 1 < D and not pair_ok(s, grid[i][d + 1]):
            return False
        return True

    while True:
        it += 1
        if (it & 255) == 0:
            now = time.time()
            if now > deadline:
                break
            if floor_cost is not None and best_cost <= floor_cost:
                break                      
            temp = T0 * (T1 / T0) ** ((now - t_start) / span)

        if s_days and rng.random() < 0.12:
            d = s_days[rng.randrange(len(s_days))]
            col = [grid[i][d] for i in range(N)]
            if rng.random() < 0.5:
                bs = [i for i in range(N) if col[i] == 'B']
                rs = [i for i in range(N) if col[i] == 'R']
                if len(bs) < 2 or not rs:          
                    continue
                i = bs[rng.randrange(len(bs))]
                j = rs[rng.randrange(len(rs))]
                new_i, new_j = ('M', 'A') if rng.random() < 0.5 else ('A', 'M')
                if used[j] + 1 > K:
                    continue
                if not fits(i, d, new_i) or not fits(j, d, new_j):
                    continue
                old_i, old_j = grid[i][d], grid[j][d]
                grid[i][d], grid[j][d] = new_i, new_j
                if not rest_ok(grid[j], d, D):
                    grid[i][d], grid[j][d] = old_i, old_j
                    continue
                oc = nurse_cost(cM[i], cA[i], cE[i]) + nurse_cost(cM[j], cA[j], cE[j])
                if new_i == 'M':
                    ncM_i, ncA_i = cM[i], cA[i] - 1
                    ncM_j, ncA_j = cM[j], cA[j] + 1
                else:
                    ncM_i, ncA_i = cM[i] - 1, cA[i]
                    ncM_j, ncA_j = cM[j] + 1, cA[j]
                nc = nurse_cost(ncM_i, ncA_i, cE[i]) + nurse_cost(ncM_j, ncA_j, cE[j])
                delta = nc - oc
                if delta <= 0 or rng.random() < pow(2.718281828, -delta / temp):
                    cM[i], cA[i] = ncM_i, ncA_i
                    cM[j], cA[j] = ncM_j, ncA_j
                    used[i] -= 1
                    used[j] += 1
                    cost += delta
                else:
                    grid[i][d], grid[j][d] = old_i, old_j
            else:
                ms = [i for i in range(N) if col[i] == 'M' and i < Ns]
                aas = [i for i in range(N) if col[i] == 'A']
                if not ms or not aas:
                    continue
                i = ms[rng.randrange(len(ms))]
                j = aas[rng.randrange(len(aas))]
                if i == j or used[i] + 1 > K:
                    continue
                old_i, old_j = grid[i][d], grid[j][d]
                grid[i][d], grid[j][d] = 'B', 'R'
                if not fits(i, d, 'B'):
                    grid[i][d], grid[j][d] = old_i, old_j
                    continue
                oc = nurse_cost(cM[i], cA[i], cE[i]) + nurse_cost(cM[j], cA[j], cE[j])
                nc = (nurse_cost(cM[i], cA[i] + 1, cE[i])
                      + nurse_cost(cM[j], cA[j] - 1, cE[j]))
                delta = nc - oc
                if delta <= 0 or rng.random() < pow(2.718281828, -delta / temp):
                    cA[i] += 1
                    cA[j] -= 1
                    used[i] += 1
                    used[j] -= 1
                    cost += delta
                else:
                    grid[i][d], grid[j][d] = old_i, old_j
            if cost < best_cost:
                best_cost = cost
                best = [row[:] for row in grid]
            continue

        d = rng.randrange(D)
        i = rng.randrange(N)
        j = rng.randrange(N)
        if i == j:
            continue
        si, sj = grid[i][d], grid[j][d]
        if si == sj:
            continue
        # K budget
        du = LOAD[sj] - LOAD[si]
        if used[i] + du > K or used[j] - du > K:
            continue
        grid[i][d], grid[j][d] = sj, si
        ok = fits(i, d, sj) and fits(j, d, si)
        if ok and si == 'R':
            ok = rest_ok(grid[i], d, D)
        if ok and sj == 'R':
            ok = rest_ok(grid[j], d, D)
        if not ok:
            grid[i][d], grid[j][d] = si, sj
            continue

        def shifted(i0, s, sign):
            x, y, z = cM[i0], cA[i0], cE[i0]
            if s == 'M':
                x += sign
            elif s == 'A':
                y += sign
            elif s == 'E':
                z += sign
            elif s == 'B':
                x += sign
                y += sign
            return x, y, z

        xi, yi, zi = shifted(i, si, -1)
        if sj == 'M':
            xi += 1
        elif sj == 'A':
            yi += 1
        elif sj == 'E':
            zi += 1
        elif sj == 'B':
            xi += 1
            yi += 1
        xj, yj, zj = shifted(j, sj, -1)
        if si == 'M':
            xj += 1
        elif si == 'A':
            yj += 1
        elif si == 'E':
            zj += 1
        elif si == 'B':
            xj += 1
            yj += 1

        delta = (nurse_cost(xi, yi, zi) + nurse_cost(xj, yj, zj)
                 - nurse_cost(cM[i], cA[i], cE[i])
                 - nurse_cost(cM[j], cA[j], cE[j]))
        if delta <= 0 or rng.random() < pow(2.718281828, -delta / temp):
            cM[i], cA[i], cE[i] = xi, yi, zi
            cM[j], cA[j], cE[j] = xj, yj, zj
            used[i] += du
            used[j] -= du
            cost += delta
            if cost < best_cost:
                best_cost = cost
                best = [row[:] for row in grid]
        else:
            grid[i][d], grid[j][d] = si, sj

    return best, best_cost




def provably_infeasible(P):
    N, D, Ns, K = P.N, P.D, P.Ns, P.K
    m, a, e, need = P.m, P.a, P.e, P.need
    if N == 0 or D == 0 or need == 0:
        return False

    n_S = sum(1 for d in range(D) if P.is_S[d])
    b_max = min(m, a, Ns)
    if n_S > 0 and b_max < 1:
        return True
    if N * K < D * need:
        return True
    for d in range(D):
        avail = 0
        s_avail = 0
        for i in range(N):
            if not P.leave[i][d]:
                avail += 1
                if i < Ns:
                    s_avail += 1
        if need - (b_max if P.is_S[d] else 0) > avail:
            return True
        if P.is_S[d] and s_avail < 1:
            return True
    if D >= 2 and N < 2 * m + e:
        return True
    if n_S > 0 and Ns * min(K // 2, (D + 1) // 2) < n_S:
        return True
    max_work = D - D // 6
    supply = 0
    for i in range(N):
        free = P.avail_after[i][0]
        cap = max_work if max_work < K else K
        supply += cap if cap < free else free
    if supply < D * need - n_S * b_max:
        return True

    return False


def write_solution(P, grid, path):
    if grid is None:
        out = {}
    else:
        out = {}
        for i in range(P.N):
            row = grid[i]
            for d in range(P.D):
                out["N%d_%d" % (i, d)] = row[d]
    with open(path, 'w') as f:
        json.dump(out, f)


def main():
    input_csv = sys.argv[1]
    output_file = sys.argv[2]
    P = Problem(input_csv)

    budget = P.T if P.T and P.T > 0 else 600.0
    deadline = START_TIME + max(1.0, budget * 0.93 - 1.0)

    if P.N == 0 or P.D == 0:
        write_solution(P, [[] for _ in range(P.N)], output_file)
        return

    if provably_infeasible(P):
        write_solution(P, None, output_file)
        return

    rng = random.Random(12345)
    best = None
    best_cost = None
    build_deadline = min(deadline,
                         START_TIME + min(0.15 * (deadline - START_TIME), 10.0))
    attempts = 0
    good = 0
    while time.time() < (build_deadline if best is not None else deadline):
        if good >= 10:
            break
        attempts += 1
        w = 1.0 if attempts % 2 else 0.3
        g = construct(P, rng, w, deadline)
        if g is not None:
            good += 1
            c = total_cost(P, g)
            if best is None or c < best_cost:
                best, best_cost = g, c
                write_solution(P, best, output_file)   

    if best is None:
        write_solution(P, None, output_file)
        return

    
    floor_cost = lower_bound(P)
    slice_len = max(2.0, min(10.0, 0.02 * budget))
    idle = 0
    slices = 0
    while time.time() < deadline - 0.05 and best_cost > floor_cost:
        slice_end = min(deadline, time.time() + slice_len)
        g, c = anneal(P, [row[:] for row in best], slice_end, rng, floor_cost)
        slices += 1
        if c < best_cost:
            best, best_cost = g, c
            write_solution(P, best, output_file)
            idle = 0
        else:
            idle += 1
            if idle >= 3 and slices >= 4:
                break

    write_solution(P, best, output_file)


if __name__ == '__main__':
    main()
