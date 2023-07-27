
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
                       'E': np.array(ldict['E']), 
                       'Q': ldict['Q'], 
                       'S': np.array(ldict['S']),
		       'Time': np.array(ldict['Time']) })
        i = j
    return i,com,iterations

def compute_jumps(qiot,jumps,S,Q):
    num=0
    q=0
    for i in range(len(S)-1):
            num=num+abs(S[i]-S[i+1])
            q=q+Q[S[i]-1]
    jumps.append(num)
    q=q+Q[S[len(S)-1]-1]
    qiot.append(q)

if __name__ == "__main__":
    if (len(sys.argv)) !=3:
        print("analyze [serialdump] [0=iot|1=stabilization]")
        sys.exit()

    if sys.argv[2] == 0:
        K,N,BMIN,BMAX,BINIT,BSAMPLING,MAX_QUALITY_LVL = [0]*7
    else:
        K,N,BMIN,BMAX,BINIT,BSAMPLING,MAX_QUALITY_LVL,EPSILON = [0]*8

    c_i = []
    q_i = []
    l_i = []
    e_i = []
    it: int = 0
    Energy, Q, Time, E, S = 0,0,0,[],[]
    execution_time = []
    jumps = []
    qiot = []
    
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
    if sys.argv[2] == "1":
        print(EPSILON)
    print(c_i)
    print(q_i)
    print(l_i)
    Tasks = []
    for x in zip(c_i, q_i, l_i):
        Tasks.append(Task(*x))
    print("-"*20)
    
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
        #-- compute jumps
        execution_time.append(Time)
        compute_jumps(qiot,jumps,S,q_i)
        print(f"S\t=\t {S}")
        print(f"Jumps\t=\t {jumps}")
        print(f"Quality\t=\t {qiot}")

    print("------------------------------------------------------------------------------------------")
    print("Quality IoT (min,max,avg): %.3f, %.3f, %.3f" % (np.array(qiot).min()/K,np.array(qiot).max()/K,np.array(qiot).mean()/K))
    print("Jumps IoT (min,max,avg): %.3f, %.3f, %.3f" % (np.array(jumps).min(),np.array(jumps).max(),np.array(jumps).mean()))
    print("Time (min,max,avg): %.3f, %.3f, %.3f" % (np.array(execution_time).min(),np.array(execution_time).max(),np.array(execution_time).mean()))
