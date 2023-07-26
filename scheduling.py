
# Please add here the date of last change, or add to a git repo.
# Antonio / 27/04/2023

import numpy as np
from collections import namedtuple



Task = namedtuple("Task","cost quality level")

def check(K,S,Bstart,Bmin,Bmax,E,Tasks,debug=False):
    """ Check that the schedule is valid and energy neutral
        return the overall quality if valid or 0 if not
    """
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

def iot_schedule_optimized(K: int,Bstart: int, Bmin: int, Bmax: int, E,Tasks):
    #print("run iot_schedule_optimized on",K,Bstart,Bmin,Bmax,Tasks,E)
    M = np.zeros( (  2,Bmax+1), dtype=int)
    I = np.zeros( (K-1,Bmax+1), dtype=int)
    k = K-1
    t = len(Tasks)-1
    for b in range(Bmax,-1,-1):
        while (t>=0):
            if (b+E[k]-Tasks[t].cost >= Bstart):
                M[k%2][b] = Tasks[t].quality
                I[k-1][b] = t+1
                break;
            t = t-1
    Mz,Iz = 0,0
    for k in range(K-2,-1,-1):
        if k == 0:
            b = Bstart
            qmax = -100
            idmax = 0
            for t in range(len(Tasks)):
                Bprime = min(b + E[k] -Tasks[t].cost,Bmax);
                if Bprime >= Bmin:
                    q = M[(k+1)%2][Bprime]
                    if (q == 0): continue
                    if (q + Tasks[t].quality > qmax):
                        qmax = q + Tasks[t].quality
                        idmax = t+1
            Mz = qmax if qmax != -100 else 0
            Iz = idmax
        else:
            for b in range(0,Bmax+1):
                qmax = -100
                idmax = 0
                for t in range(len(Tasks)):
                    Bprime = min(b+E[k]-Tasks[t].cost,Bmax);
                    if (Bprime >= Bmin):
                        q = M[(k+1)%2][Bprime]
                        if (q == 0): continue
                        if (q + Tasks[t].quality > qmax):
                            qmax = q + Tasks[t].quality
                            idmax = t+1
                M[k%2][b] = qmax if qmax != -100 else 0
                I[k-1][b] = idmax

    S = [0]*K
    B = Bstart
    S[0] = Iz-1
    if (S[0] < 0): return (S,0) 
    B = min(B + E[0] - Tasks[S[0]].cost,Bmax)
    assert(B >= Bmin)
    for i in range(1,K):
        S[i] = I[i-1][B]-1
        if (S[i] < 0): return (S,0)
        B = min(B + E[i] - Tasks[S[i]].cost,Bmax)
        assert(B >= Bmin)
    assert(B >= Bstart)
    qmax = Mz if K%2==0 else M[(K+1)%2][Bstart]
    assert(qmax == sum(Tasks[s].quality for s in S))
    return (S,qmax)

def iot_schedule_nomem(slots,Bstart,Bmin,Bmax,Eprod,Tasks,Bend):
    # basic checks
    assert(len(Eprod) == slots)
    assert(Bmin < Bstart < Bmax)    
    M = np.zeros( (2,Bmax+1), dtype=int)
    index = -1
    idmax = 0
    for i in range(slots-1,-1,-1):
        for B in range(0,Bmax+1):
            qmax = -100
            idmax = 0
            if (i == slots-1):
                for t,task in enumerate(Tasks):
                    if (B-task.cost+Eprod[i] >= Bend and task.quality > qmax):
                        qmax = task.quality
                        idmax = t+1
            else:
                for t,task in enumerate(Tasks):
                    Bprime = min(B-task.cost+Eprod[i],Bmax)
                    if (Bprime >= Bmin):
                        q = M[(i+1)%2][Bprime]
                        if (q == 0): continue
                        if (q + task.quality > qmax):
                            qmax = q + task.quality
                            idmax = t+1
            M[i%2][B] =  qmax if qmax != -100 else 0
            if (i == 0 and B == Bstart): 
                index = idmax    
    return(M[slots%2][Bstart],index)

def iot_schedule_exact(K,Bstart,Bmin,Bmax,Eprod,Tasks):
    """
    K = number of slots in a day
    Battery: Bmin < Bstart < Bmax 
    PanelProducton:  Eprod | len(Eprod) == slots
    Tasks: ordered from lowest cost,quality to greatest
    
    This is the original algorithm of IoT Journal without sampling.
    The code is maintained simple even if not efficient. 
    Prefer readability over memory or speed.

    output: schedule and quality, if quality = 0 no valid schedule exist.
    """
    # basic checks
    assert(len(Eprod) == K)
    assert(Bmin < Bstart < Bmax)    
    M = np.zeros( (K,Bmax+1), dtype=int)
    I = np.zeros( (K,Bmax+1), dtype=int)
    for i in range(K-1,-1,-1):
        for B in range(0,Bmax+1):
            qmax = -100
            idmax = 0
            if i == K-1:
                for t,task in enumerate(Tasks):
                    if B - task.cost + Eprod[i] >= Bstart and task.quality > qmax:
                        qmax = task.quality
                        idmax = t+1
            else:
                for t,task in enumerate(Tasks):
                    Bprime = min(B - task.cost + Eprod[i], Bmax)
                    if Bprime >= Bmin:
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
        B = min(B + Eprod[i] - Tasks[ S[i] ].cost, Bmax)
        assert(B >= Bmin)
    assert(B >= Bstart)
    return (S,sum(Tasks[s].quality for s in S))

#  -- CARFAGNA --

def carfagna_schedule(K, Bstart, Bmin, Bmax, maxQ,E,Tasks):
    maxq_ps = 0
    maxq_cs = 0
    B = np.zeros((2,K*maxQ+1),dtype=np.int16)
    S = np.zeros((K,K*maxQ+1),dtype=np.int8)
    for k in range(K):
        maxq_cs = -1
        if (k == 0):
            for q in range(maxQ+1):
                currentBmax = 0
                idMax = 0
                for t,task in enumerate(Tasks):
                    Br = Bstart + E[0] - task.cost
                    if  task.level == q and Br >= Bmin and Br >= currentBmax:
                        currentBmax = Br
                        idMax = t+1
                        maxq_cs = q
                B[0][q] = min(currentBmax,Bmax)
                S[0][q] = idMax
        else:
            for q in range(maxq_ps+maxQ+1):
                currentBmax = 0
                idMax = 0
                for t,task in enumerate(Tasks):
                     Bprec = B[(k-1)%2][q-task.level]
                     if Bprec == 0: continue
                     Br = Bprec + E[k] - task.cost
                     if q >= task.level and \
                        q - task.level <= maxq_ps and Br >= Bmin and Br > currentBmax:
                        currentBmax = Br
                        idMax = t+1
                        maxq_cs = q
                B[k%2][q] = min(currentBmax,Bmax)
                S[k][q] = idMax
        maxq_ps = maxq_cs
        if maxq_ps == -1:
            print("no solution found")
            return ([],0)
    upperbound = maxq_cs
    while upperbound >= 0 and (B[(K-1)%2][upperbound] < Bstart or B[(K-1)%2][upperbound] == 0):
         upperbound -= 1
    if upperbound < 0:
        return ([],0)
    t = upperbound
    schedule = np.zeros(K,dtype=np.int8)
    for s in range(K-1,-1,-1):
        schedule[s] = S[s][t] - 1
        t -= Tasks[ schedule[s] ].level
    return (schedule,sum(Tasks[s].quality for s in schedule))