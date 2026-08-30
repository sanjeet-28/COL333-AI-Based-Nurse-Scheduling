import sys
import copy

def solve(N, D, N_s, N_g, m, a, e, max_shifts, days, leaves):
    sys.setrecursionlimit(20000)
    roster = [[None for _ in range(D)] for _ in range(N)]
    workload = [0] * N
    consec_work = [0] * N
    prev_shift = [None] * N
    
    # Pre-parse leaves for faster lookup
    leave_set = set()
    idx = 0
    for d in range(D):
        for n in range(N):
            if leaves[idx] == 'L':
                leave_set.add((n, d))
            idx += 1

    def get_legal_shifts(nurse, d, req, consec, wl, ps):
        if (nurse, d) in leave_set:
            return ['R']
        
        shifts = []
        is_surg = (nurse < N_s)
        
        # working shifts require workload < max_shifts and consec < 5
        can_work = (wl < max_shifts) and (consec < 5)
        
        if can_work:
            if req.get('B', 0) > 0 and is_surg and ps not in ['E', 'M', 'B']:
                shifts.append('B')
            if req.get('M', 0) > 0 and ps not in ['E', 'M', 'B']:
                shifts.append('M')
            if req.get('A', 0) > 0:
                shifts.append('A')
            if req.get('E', 0) > 0 and ps != 'B':
                shifts.append('E')
                
        shifts.append('R')
        return shifts

    def assign_shifts(d, idx, shifts_to_assign, unassigned_nurses, last_nurse=-1, req=None):
        if idx == len(shifts_to_assign):
            saved_state = {}
            for n in unassigned_nurses:
                saved_state[n] = (roster[n][d], prev_shift[n], consec_work[n])
                roster[n][d] = 'R'
                prev_shift[n] = 'R'
                consec_work[n] = 0
                
            if solve_day(d + 1): return True
            
            for n in unassigned_nurses:
                roster[n][d], prev_shift[n], consec_work[n] = saved_state[n]
            return False
            
        shift = shifts_to_assign[idx]
        capable = []
        for n in unassigned_nurses:
            if idx > 0 and shifts_to_assign[idx] == shifts_to_assign[idx-1]:
                if n <= last_nurse:
                    continue
            
            if shift in get_legal_shifts(n, d, req, consec_work[n], workload[n], prev_shift[n]):
                capable.append(n)
                
        # Sort capable by workload to distribute shifts
        capable.sort(key=lambda n: workload[n])
                
        for n in capable:
            saved = (roster[n][d], prev_shift[n], consec_work[n], workload[n])
            roster[n][d] = shift
            prev_shift[n] = shift
            consec_work[n] += 1
            workload[n] += 1
            unassigned_nurses.remove(n)
            
            if assign_shifts(d, idx + 1, shifts_to_assign, unassigned_nurses, n, req):
                return True
                
            unassigned_nurses.add(n)
            roster[n][d], prev_shift[n], consec_work[n], workload[n] = saved
            
        return False

    def solve_day(d):
        if d == D: return True
        
        b_min = 1 if days[d] == 'S' else 0
        b_max = min(m, a, N_s) if days[d] != 'G' else 0
        
        for b_total in range(b_max, b_min - 1, -1):
            req = {'M': m - b_total, 'A': a - b_total, 'E': e, 'B': b_total}
            
            shifts_to_assign = ['B']*req['B'] + ['E']*req['E'] + ['M']*req['M'] + ['A']*req['A']
            
            if assign_shifts(d, 0, shifts_to_assign, set(range(N)), -1, req):
                return True
                
        return False

    if solve_day(0): return roster
    return None

import json
from part_a import parse_input
if __name__ == '__main__':
    import time
    t0 = time.time()
    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input('checker/test-cases/suite_001/test437.csv')
    roster = solve(N, D, Ns, Ng, m, a, e, max_shifts, days, leaves)
    print("Solved!" if roster else "Failed", f"Time: {time.time()-t0:.3f}s")
