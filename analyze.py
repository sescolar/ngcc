
# Please add here the date of last change, or add to a git repo.
# Antonio / 27/04/2023


import sys
import numpy as np
from scheduling import Task,iot_schedule_exact,carfagna_schedule

np.set_printoptions(linewidth=100)


#### main program

def parse_input(lines):
    iterations = []
    i = 0
    while "it,Energy" not in lines[i]: i += 1
    if i == 0:
        print("Error in input file.")
        sys.exit(0)
    # parse all variabile in input
    com = ""
    inside = False
    for l in lines[0:i]:
        if not inside and '[' in l and ']' not in l:
           com += l 
           inside = True
        else:
            if inside and ']' not in l:
                com += l
            elif inside and ']' in l:
                com += l + "\n"
            else:
                com += l + "\n"
    # parse iteration data
    it: int = 0
    Energy: int = 0
    Q: int = 0
    Time: int = 0
    E,S = [],[]
    print(f"start parsing {len(lines)} lines:")
    inside = True
    while True:
        j = i+1
        ldict = {}
        while j<len(lines) and "it,Energy" not in lines[j]: 
            j += 1
        if j-i<5:
           break 
        exec("\n".join(lines[i:j]),globals(),ldict)
        iterations.append({ 'it': ldict['it'], 
                       'Energy': ldict['Energy'], 
                       'Q': ldict['Q'], 
                       'E': np.array(ldict['E']), 
                       'S': np.array(ldict['S']),
		       'Time': np.array(ldict['Time']) })
        i = j
    return i,com,iterations

def check(E,S,Bstart,Bmin,Bmax,Cost,Quality):
    k = len(S)
    battery = Bstart
    q = 0
    for i in range(k):
        battery = min(battery-Cost[S[i]-1]+E[i],Bmax)
        q += Quality[S[i]-1]
        if battery < Bmin: print("bmin violated:",battery)
    if battery < Bstart:
        print("Not Energy Neutral:", battery)



if __name__ == "__main__":
    K,N,BMIN,BMAX,BINIT,BSAMPLING,MAX_QUALITY_LVL = [0]*7
    c_i = []
    q_i = []
    l_i = []
    e_i = []
    it: int = 0
    Energy, Q, Time, E, S = 0,0,0,[],[]
    
    if len(sys.argv) == 1:
        print("analyze [serialdump]")
        sys.exit()
#   option = int(sys.argv[2]) if len(sys.argv) == 3 else 0
    
    # read input
    f = open(sys.argv[1],encoding="utf8")
    lines = f.read().split("\n")
    i,com,iterations = parse_input(lines)
    exec(com)
    #--print header
    print("-"*20)
    print(K,N)
    print(BMIN,BMAX,BINIT,BSAMPLING)
    print(MAX_QUALITY_LVL)
    print(c_i)
    print(q_i)
    print(l_i)
    Tasks = []
    if len(l_i) == 0:
        l_i = [0]*K
        alg_input = "IoT"
    else:
        alg_input = "Carfagna"
    for x in zip(c_i, q_i, l_i):
        Tasks.append(Task(*x))
    print("-"*20)
    
    opt_ratio1 = []
    opt_ratio2 = []
    execution_time1 = []
    #-- start analysis
    for data in iterations:
        it = data['it']
        Q = data['Q']
        Energy = data['Energy']
        E = data['E']
        S = data['S']
	#added
        Time = data['Time']
        print(f"iteration: {it}, E = {E}")
        (s1,quality1) = iot_schedule_exact(K,BINIT,BMIN,BMAX,E,Tasks)
        (s2,quality2) = carfagna_schedule(K,BINIT,BMIN,BMAX,MAX_QUALITY_LVL,E,Tasks)
        
        #-- compute averages
        opt_ratio1.append(100*Q/quality1)
        opt_ratio2.append(100*Q/quality2)
        execution_time1.append(Time)
 
        print(f"quality input {alg_input}    =\t  {Q} \t {Q/quality1*100: .2f}")
        print("quality python exact      = ",quality1)
        if alg_input=='Carfana':
            print("quality python carfagna   = ",quality2)
        print(f"S input {alg_input}\t= {S}")
        print(f"S python exact\t= {np.array(s1)+1}")
        if alg_input=='Carfana':
            print(f"S python carfagna\t= {np.array(s2)+1}")
        print(f"Time input {alg_input}    =  {Time}")
        check(E,S,BINIT,BMIN,BMAX,c_i,q_i)

        # do not use for now..
        # if option == 1:
        #     print("%2d" % (it),"\t",E)
        # elif option == 2:
        #     print("%2d" % (it),"\t",E)
        #     (s,q) = ScheduleClassic(K,BINIT,BMIN,BMAX,E,Tasks)
        #     print(" ",q,end=" - ")
        #     print(f"S = {s}" if q!=0 else "")
        # elif option == 3:
        #     print("%2d" % (it),"\t",E)
        #     (s,q) = ScheduleClassic(K,BINIT,BMIN,BMAX,E,Tasks)
        #     print(" ",q,end=" - ")
        #     print(f"S = {s}" if q!=0 else "")
        #     (s,q) = schedule(K,BINIT,BMIN,BMAX,E,Tasks)
        #     print(" ",q,end=" - ")
        #     print(f"S = {s}" if q!=0 else "")
        # elif option == 0:   
        #     print("%2d " % (it),Energy,Time,end=" - \n")
        #     (Sn,q) = schedule(K,BINIT,BMIN,BMAX,E,Tasks)
        #     print("\t",E)
        #     print("\tS Esatta   ",Sn,q)
        #     print("\tS Arduino  ",S,Q,"%.1f%%" % (100*Q/q))
        # elif option == 4:
        #     print("%2d" % (it)," ",E)
        #     (s,q) = ScheduleClassic(K,BINIT,BMIN,BMAX,E,Tasks)
        #     print("    ",S,Q,check(K,S,BINIT,BMIN,BMAX,E,Tasks),q)
    print("Quality IoT (min,max,avg): %.3f, %.3f, %.3f" % (np.array(opt_ratio1).min(),np.array(opt_ratio1).max(),np.array(opt_ratio1).mean()))
    print("Quality Carfagna (min,max,avg): %.3f, %.3f, %.3f" % (np.array(opt_ratio2).min(),np.array(opt_ratio2).max(),np.array(opt_ratio2).mean()))
    print("Time (min,max,avg): %.3f, %.3f, %.3f" % (np.array(execution_time1).min(),np.array(execution_time1).max(),np.array(execution_time1).mean()))
