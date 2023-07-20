import sys
import numpy as np
import math
from collections import namedtuple

Task = namedtuple("Task","cost quality")

def check(K,S,Bstart,Bmin,Bmax,E,Tasks,debug=False):
    b = Bstart
    q = 0
    for i in range(K):
        bnew = min(b+E[i]-Tasks[S[i]].cost,Bmax)
        q += Tasks[S[i]].quality
        if debug: print("%2d :  %4d - %3d + %3d = %4d : %4d" %
        (S[i],b,Tasks[S[i]].cost,E[i],bnew,q))
        b = bnew
        if (b < Bmin): return 0
    if (b < Bstart):
        return 0
    return sum(Tasks[s].quality for s in S)

def ScheduleClassic(slots,Bstart,Bmin,Bmax,Eprod,Tasks):
    """
    slots = K = number of slots in a day
    Battery: Bmin < Bstart < Bmax 
    PanelProducton:  Eprod | len(Eprod) == slots
    Tasks: ordered from lowest cost,quality to greatest
    """
    # basic checks
    assert(len(Eprod) == slots)
    assert(Bmin < Bstart < Bmax)    
    M = np.zeros( (slots,Bmax+1), dtype=int)
    I = np.zeros( (slots,Bmax+1), dtype=int)
    for i in range(slots-1,-1,-1):
        for B in range(0,Bmax+1):
            qmax = -100
            idmax = 0
            if (i == slots-1):
                for t,task in enumerate(Tasks):
                    if (B-task.cost+Eprod[i] >= Bstart and task.quality > qmax):
                        qmax = task.quality
                        idmax = t+1
            else:
                for t,task in enumerate(Tasks):
                    Bprime = min(B-task.cost+Eprod[i],Bmax)
                    if (Bprime >= Bmin):
                        q = M[i+1][Bprime]
                        if (q == 0): continue
                        if (q + task.quality > qmax):
                            qmax = q + task.quality
                            idmax = t+1
            M[i][B] =  qmax if qmax != -100 else 0
            I[i][B] = idmax
    S = [0]*K
    B = Bstart
    for i in range(K):
        S[i] = I[i][B]-1
        if (S[i] < 0): return (S,0)
        B = min(B + Eprod[i] - Tasks[ S[i] ].cost,Bmax)
        assert(B >= Bmin)
    assert(B >= Bstart)
    return(S,sum(Tasks[s].quality for s in S))

def ScheduleNew(slots,Bstart,Bmin,Bmax,Eprod,Tasks,eps=0.5):
    """
    slots = K = number of slots in a day
    Battery: Bmin < Bstart < Bmax 
    PanelProducton:  Eprod | len(Eprod) == slots
    Tasks: ordered from lowest cost,quality to greatest
    """
    # basic checks
    assert(len(Eprod) == slots)
    assert(Bmin < Bstart < Bmax)    
    M = np.zeros( (slots,Bmax+1), dtype=int)
    I = np.zeros( (slots,Bmax+1), dtype=int)
    
    for i in range(slots-1,-1,-1):      # for each slot
        for B in range(Bmax,-1,-1):     # for each level of battery (reversed)
            qmax = -100
            idmax = 0
            if (i == slots-1):          # last slot take the optimum
                for t,task in enumerate(Tasks):
                    if (B-task.cost+Eprod[i] >= Bstart and task.quality > qmax):
                        qmax = task.quality
                        idmax = t+1
            else:
                for t,task in enumerate(Tasks):
                    Bprime = min(B-task.cost+Eprod[i],Bmax)
                    if (Bprime >= Bmin):
                        q = M[i+1][Bprime]
                        if (q == 0): continue
                        j = I[i+1][Bprime]-1
                        penalty = int(eps * (abs(task.quality - Tasks[j].quality) - Tasks[0].quality))
                        #print(q,task.quality,penalty, q + task.quality - penalty )
                        #penalty =  eps*(abs(j-t)-1) if abs(j-t)>1 else 0
                        #penalty =  eps*(abs(t-j)-1) if t-j>1 else 0
                        if (q + task.quality - penalty > qmax):
                            qmax = q + task.quality - penalty
                            idmax = t+1
            M[i][B] =  qmax if qmax != -100 else 0
            I[i][B] = idmax
    S = [0]*K
    B = Bstart
    for i in range(K):
        S[i] = I[i][B]-1
        if (S[i] < 0): return (S,0)
        B = min(B + Eprod[i] - Tasks[ S[i] ].cost,Bmax)
        assert(B >= Bmin)
    assert(B >= Bstart)
    # note that we compute the quality like without penalty
    return(S,sum(Tasks[s].quality for s in S))     



K = 24
N = 10
#test1
#c_i = [  1, 16, 27, 38, 49, 60, 70, 81, 92,103]
#q_i = [  1, 16, 27, 37, 48, 59, 68, 79, 90,100]


#test2
c_i = [  1, 16, 24, 37, 41, 53, 60, 71, 82, 95]
q_i = [  1, 11, 27, 31, 48, 59, 65, 79, 86,100]

#test3
#c_i = [  1, 16, 27, 38, 49, 60, 70, 81, 92,103]
#q_i = [  1, 10, 25, 35, 45, 55, 68, 85, 92,100]

Tasks = []
for x in zip(c_i,q_i):
    Tasks.append(Task(*x))
BMIN = 160
BSTART = 1800
BMAX = 2000
E = np.array([ 0, 0,0,0,0, 0,0,3,45,133,215,285,327,339,322,255, 60, 66, 63, 23,9,0,0,0])
E = E * 0.9
E = E.astype(int)

# print("Quality Jumps: ")
# for a in q_i:
#     for b in q_i:
#         print(abs(a-b),end= " ")
#     print("")
# print("-"*80)

def RunClassic(Tasks):
    S,q = ScheduleClassic(K,BSTART,BMIN,BMAX,E,Tasks)
    print("Schedule = ", S," quality = ",q)
    j = list(abs(S[i]-S[i+1]) for i in range(len(S)-1))
    print("Jumps    = ", j , " ", sum(j), " ", max(j) )

def RunNew(Tasks):
    l = []
    for eps in np.arange(0,10,0.2):
        S,q = ScheduleNew(K,BSTART,BMIN,BMAX,E,Tasks,eps)
        j = list(abs(S[i]-S[i+1]) for i in range(len(S)-1))
        mj=max(j)
        l.append((S,q,eps, j, mj ))
        if mj == 1: break
    S,q,eps,j,mj = l[-1]
    print("NewSched = ",S,q)
    print("Jumps =    ",j," ",sum(j)," ",mj,"       besteps = ",eps)
    return eps

def ChangeTasks(d):
    q = np.array(q_i) + d
    q[q<0] = 1
    q = q.astype(int)
    Tasks = []
    for x in zip(c_i,q):
        Tasks.append(Task(*x))
    return q,Tasks

RunClassic(Tasks)
print("-"*80)
S,q = ScheduleNew(K,BSTART,BMIN,BMAX,E,Tasks,0.5)
print("NewSched = ",S,q)
j = list(abs(S[i]-S[i+1]) for i in range(len(S)-1))
print("Jumps =    ", j ," total = ",sum(j)," max = ",max(j))
sys.exit(0)



eps = RunNew(Tasks)
print("-"*80)

q,Tasks = ChangeTasks(-5)
print("Q   =  ",q)
RunClassic(Tasks)
RunNew(Tasks)
S,q = ScheduleNew(K,BSTART,BMIN,BMAX,E,Tasks,eps)
print(f"eps = {eps} ", max(list(abs(S[i]-S[i+1]) for i in range(len(S)-1))))
print("-"*80)

q,Tasks = ChangeTasks(-10)
print("Q   =  ",q)
RunClassic(Tasks)
RunNew(Tasks)
S,q = ScheduleNew(K,BSTART,BMIN,BMAX,E,Tasks,eps)
print(f"eps = {eps} ", max(list(abs(S[i]-S[i+1]) for i in range(len(S)-1))))
print("-"*80)


q,Tasks = ChangeTasks(-15)
print("Q   =  ",q)
RunClassic(Tasks)
RunNew(Tasks)
S,q = ScheduleNew(K,BSTART,BMIN,BMAX,E,Tasks,eps)
print(f"eps = {eps} ", max(list(abs(S[i]-S[i+1]) for i in range(len(S)-1))))
print("-"*80)
