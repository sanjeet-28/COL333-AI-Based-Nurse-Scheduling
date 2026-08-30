import sys 
import csv
import json

def parse_input(input_csv):
    """Reads the CSV and initializes problem variables."""
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

def solve(N, D, N_s, N_g, m, a, e, max_shifts, days, leaves):
    roster = [[None for _ in range(D)] for _ in range(N)]
    workload = [0] * N
    consec_work = [0] * N
    prev_shift = [None] * N

    def get_legal_shifts(nurse, d, req, cw, wl, ps):
        shifts = []
        is_leave = leaves[nurse * D + d] == 'L'
        is_surg = nurse < N_s
        
        if is_leave:
            shifts.append('R')
            return shifts

        if cw == 5:
            shifts.append('R')
            return shifts

        if req['B'] > 0 and is_surg and ps not in ['M', 'B', 'E'] and days[d] != 'G' and wl + 2 <= max_shifts:
            shifts.append('B')
        if req['M'] > 0 and ps not in ['M', 'B', 'E'] and wl + 1 <= max_shifts:
            shifts.append('M')
        if req['A'] > 0 and ps != 'B' and wl + 1 <= max_shifts:
            shifts.append('A')
        if req['E'] > 0 and ps != 'B' and wl + 1 <= max_shifts:
            shifts.append('E')
        
        shifts.append('R')
        return shifts

    sys.setrecursionlimit(20000)
    
    def assign_nurses(d, unassigned_nurses, req):
        if not unassigned_nurses:
            if req['M'] == 0 and req['A'] == 0 and req['E'] == 0 and req['B'] == 0:
                return solve_day(d + 1)
            return False

        # Precompute legal shifts
        legal_shifts = {}
        for nurse in unassigned_nurses:
            l_shifts = get_legal_shifts(nurse, d, req, consec_work[nurse], workload[nurse], prev_shift[nurse])
            if not l_shifts:
                return False
            legal_shifts[nurse] = l_shifts

        cap_M = cap_A = cap_E = cap_B = 0
        cap_M_or_B = 0
        cap_A_or_B = 0
        cap_M_or_A_or_B = 0
        cap_W = 0
        
        for nurse, l_shifts in legal_shifts.items():
            has_M = 'M' in l_shifts
            has_A = 'A' in l_shifts
            has_E = 'E' in l_shifts
            has_B = 'B' in l_shifts
            
            if has_B: cap_B += 1
            if has_M: cap_M += 1
            if has_A: cap_A += 1
            if has_E: cap_E += 1
            if has_M or has_B: cap_M_or_B += 1
            if has_A or has_B: cap_A_or_B += 1
            if has_M or has_A or has_B: cap_M_or_A_or_B += 1
            if has_M or has_A or has_E or has_B: cap_W += 1

        if cap_B < req['B']: return False
        if cap_E < req['E']: return False
        if cap_M_or_B < req['M'] + req['B']: return False
        if cap_A_or_B < req['A'] + req['B']: return False
        if cap_M_or_A_or_B < req['M'] + req['A'] + req['B']: return False
        if cap_W < req['M'] + req['A'] + req['E'] + req['B']: return False

        best_nurse = min(unassigned_nurses, key=lambda n: (len(legal_shifts[n]), workload[n]))
        
        # Value ordering: prefer assigning working shifts over R
        # Order by restrictiveness: A (least), E, M, B (most).
        order = ['A', 'E', 'M', 'B', 'R']
        
        for shift in order:
            if shift in legal_shifts[best_nurse]:
                roster[best_nurse][d] = shift
                req[shift] -= 1 if shift != 'R' else 0
                
                prev = prev_shift[best_nurse]
                prev_cw = consec_work[best_nurse]
                prev_wl = workload[best_nurse]
                
                prev_shift[best_nurse] = shift
                if shift != 'R':
                    consec_work[best_nurse] += 1
                    workload[best_nurse] += 2 if shift == 'B' else 1
                else:
                    consec_work[best_nurse] = 0
                    
                unassigned_nurses.remove(best_nurse)
                
                if assign_nurses(d, unassigned_nurses, req):
                    return True
                    
                unassigned_nurses.add(best_nurse)
                roster[best_nurse][d] = None
                req[shift] += 1 if shift != 'R' else 0
                prev_shift[best_nurse] = prev
                consec_work[best_nurse] = prev_cw
                workload[best_nurse] = prev_wl
                
        return False

    def solve_day(d):
        if d == D:
            return True
            
        b_min = 1 if days[d] == 'S' else 0
        b_max = min(m, a) if days[d] != 'G' else 0
        
        # Iterating over possible B values.
        for b_total in range(b_min, b_max + 1):
            req = {'M': m - b_total, 'A': a - b_total, 'E': e, 'B': b_total, 'R': 0}
            unassigned_nurses = set(range(N))
            if assign_nurses(d, unassigned_nurses, req):
                return True
        return False

    if solve_day(0):
        return roster
    return None

if __name__ == '__main__': 
    if len(sys.argv) < 3:
        sys.exit(1)
    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(sys.argv[1])
    output_file = sys.argv[2]
    
    roster = solve(N, D, Ns, Ng, m, a, e, max_shifts, days, leaves)
    
    if roster:
        out = {}
        for n in range(N):
            for d in range(D):
                out[f"N{n}_{d}"] = roster[n][d]
        with open(output_file, 'w') as f:
            json.dump(out, f, indent=4)
    else:
        with open(output_file, 'w') as f:
            json.dump({}, f)
