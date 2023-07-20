#include <assert.h>

#define min(a,b)   ((a)<=(b)?(a):(b))
#define max(a,b)   ((a)>=(b)?(a):(b))
#define SEED       124
#define VARIATION    1


#define K 24
#define N_ITERATION   10
#define slotDurationPercentage  (24.0/K)

#define BMAX              2000
#define BMIN              160
#define B_INIT            1800

#define F(a) (a)

// parameter for the precision of the classic algorithm 'with sampling'
#define P   1
#define BATTERY_SAMPLING  (int((BMAX-BMIN)*P)) // maximum = BMAX-BMIN, 1200, 800, 400, 100
// parameter for the precision of the new algorithm 
#define MAX_QUALITY_LVL 100             // maximum = 100 (it is related to the quality as a percentage)

#define mAh_per_lvl      ((float)(BMAX-BMIN)/BATTERY_SAMPLING)
#define level_to_mah(l)  short(round((l)*(mAh_per_lvl))+BMIN) 
#define mah_to_level(b)  short((b-BMIN)/(mAh_per_lvl))

/**************************************** TASK MODEL *******************************/
#define N_TASKS   10
#define ACTIVE_SYSTEM_CONSUMPTION   124
#define IDLE_SYSTEM_CONSUMPTION      22 // idle is higher, we must check it

struct Task {
    uint8_t q_perc;    // 1 <= q_perc <= 100%
    uint8_t c_mAh;
};
struct Task tasks[N_TASKS];

void GenerateTasks(void)
{
    int i;

    tasks[0].c_mAh  = 1;
    tasks[0].q_perc = 1;
    for(i=1; i<N_TASKS; i++)
        tasks[i].c_mAh = ceil(((((float)(i-1.0) / 10.0) * ACTIVE_SYSTEM_CONSUMPTION) +
                        ((1 - (((float) (i-1.0)) / 10.0)) * IDLE_SYSTEM_CONSUMPTION)) *
                        slotDurationPercentage);
   float scale = 100.0 / tasks[N_TASKS-1].c_mAh;
   for (i=0; i<N_TASKS; i++)
        tasks[i].q_perc = ceil(tasks[i].c_mAh*scale);
}

/************************************** END TASK MODEL *******************************/


/**************************************** PANEL MODEL *******************************/

#define MAX_OVERPRODUCTION           20
#define MAX_UNDERPRODUCTION          40
#define SUNSET                       19
#define SUNRISE                       8

uint16_t E_h[24]     // Hourly Energy harvested 
// October 
= { 0,0,0,0,0,0,0,0,19,110,224,285,335,350,331,283,134,20,18,8,0,0,0,0 };

uint16_t E_h_v[24]  = { 0 };    // Hourly Energy harvested varied
uint16_t E_s_mAh[K] = { 0 };    // Final Energy harvested per slot in mAh

void InitializeEnergyHarvested(void)
{
  uint16_t total1 = 0;
  uint16_t i;

  for(i=0; i<24; i++) total1 += E_h[i];
  if (K >= 24) {
    uint16_t s = 0;
    for (i=0; i<24; i++)
      for (uint8_t j=0; j<(K/24); j++)
        s+= E_s_mAh[(i*K/24)+j] = (int)(E_h[i] * slotDurationPercentage);
    uint8_t r = total1 - s;
    for (uint8_t j=K/2; r>0 && j<K; j++) {
      E_s_mAh[j] += 1; r--;
    }
  } else {
    uint8_t scale = 24/K;
    for (i=0; i<K; i++) {
      E_s_mAh[i] = 0;
      for (uint8_t j=i*scale; j<(i+1)*scale; j++) {
        E_s_mAh[i] += E_h[j];
      }
    }
  }
}


void update_panel() 
{
  uint8_t coin;
  uint8_t pos;
  uint8_t variation;
  uint8_t i;
  // Change the energy production of the panel randomly
  // First it changes the production for each hour. then
  // we adapt the production to the slot size.
  
  for (i=0; i<24; i++) {
    if (SUNRISE <= i && i <= SUNSET) {
        if (!VARIATION) coin = 2; else coin = rand() % 3;
        switch (coin) {
        case 0 :
            variation = 100 + (rand() % (MAX_OVERPRODUCTION + 1));
            break;
        case 1 :
            variation = 100 - (rand() % (MAX_UNDERPRODUCTION + 1));
            break;
        case 2 :
            variation = 100;
            break;
        }
        E_h_v[i] = min((int)(E_h[i] * (float)variation / 100),520);   // 520 is the maximum from the panel
    }
    // if K>24 we must spread the production between K/24 slots
    for (int8_t j=0; (K >= 24) && j<(K/24); j++)
      E_s_mAh[(i * K / 24) + j] = (int)(E_h_v[i] * slotDurationPercentage);
  }
  // if K < 24 we must add the production to slot longer than one hour
  if (K < 24) {
    uint8_t scale = 24/K;
    for (i=0; i<K; i++) {
      E_s_mAh[i] = 0;
      for (uint8_t j=i*scale; j<(i+1)*scale; j++) {
        E_s_mAh[i] += E_h_v[j];
      }
    }
  }
  // When we split the production, we loose some watt, this spread them in the
  // center slots. So we run the schedule with the same total production.
  if (K>24) {
    uint16_t total = 0;
    for (i=0; i<24; i++) total += E_h_v[i];
    uint16_t total2 = 0;
    for (i=0; i<K; i++) total2 += E_s_mAh[i];
    uint8_t r = total - total2;
    for (uint8_t j=K/2; r>0 && j<K; j++) {
      E_s_mAh[j] += 1; r--;
    }
  }  
}  

// **************** END PANEL MODEL **********************

uint16_t Q[2][BATTERY_SAMPLING+1] = { 0 };         // DP: Quality Table
uint8_t  S[K][BATTERY_SAMPLING+1];                  // DP: Scheduling Table 
uint8_t NS[K];                                     // Final Scheduling 

void ClearQS()
{
  memset(Q,0,sizeof(Q));
  memset(S,0,sizeof(S));
}


char buf[60];
void PrintParameters(void) {
  int i;
  
  Serial.flush();
  Serial.print(F("\n#----------------------------------------------\n"));
  Serial.print(F("K = ")); Serial.println(K);
  Serial.print(F("N = ")); Serial.println(N_TASKS);

  Serial.print(F("BMIN = ")); Serial.println(BMIN);
  //Serial.print(","); Serial.println(mah_to_level(BMIN));

  Serial.print(F("BINIT = ")); Serial.println(B_INIT);
  //Serial.print(","); Serial.println(mah_to_level(B_INIT));

  Serial.print(F("BMAX = ")); Serial.println(BMAX);
  //Serial.print(","); Serial.println(mah_to_level(BMAX));

  Serial.print(F("BSAMPLING = ")); Serial.println(BATTERY_SAMPLING);
  Serial.print(F("EnergyForLevel = ")); Serial.println(mAh_per_lvl);
  Serial.print(F("MAX_QUALITY_LVL = ")); Serial.println(MAX_QUALITY_LVL);

  Serial.print(F("\nc_i = ["));
  for (i=0; i<N_TASKS; i++) {
    sprintf(buf,"%3d%c",tasks[i].c_mAh,(i==N_TASKS-1?']':','));
    Serial.print(buf);
  }
  Serial.print("\n");
  Serial.print(F("q_i = ["));
  for (i=0; i<N_TASKS; i++) {
      sprintf(buf,"%3d%c",tasks[i].q_perc,(i==N_TASKS-1?']':','));
      Serial.print(buf);
  }
  Serial.print("\n");

  Serial.print(F("\ne_i = ["));
  for (i=0; i<24; i++) {
      sprintf(buf,"%3d%c",E_h[i],(i==24-1?']':','));
      Serial.print(buf);
  }
  Serial.print(F("\nE_i = ["));
  for (i=0; i<K; i++) {
      sprintf(buf,"%3d%c",E_s_mAh[i],(i==K-1?']':','));
      if ((i+1) % 25 == 0) Serial.print("\n");
      Serial.print(buf);
  }
  Serial.print(F("\n#----------------------------------------------\n"));
}
                           
void scheduleTasks(uint16_t E[K], uint16_t Q)
{
  uint16_t BresL = mah_to_level(B_INIT);
  uint16_t Bres_mAh, q = 0;
  uint8_t i = 0;

  for (i=0; i<K; i++) {
    NS[i] = S[i][BresL];
   // printf("%d \n",NS[i]);
    assert(NS[i]>0);
    Bres_mAh = level_to_mah(BresL);
    Bres_mAh = min(Bres_mAh - tasks[ NS[i]-1 ].c_mAh + E[i], BMAX);
    q += tasks[NS[i]-1].q_perc;
    assert(Bres_mAh >= BMIN);
    BresL = mah_to_level(Bres_mAh);
  }
  assert(Bres_mAh >= B_INIT);
  //assert(q == Q);     /* COMMENT OUT */
}

int schedule(uint16_t E[])
{
  int8_t   t,idmax;
  int16_t  b,Br;
  int16_t   k = K-1;       // start in the last slot
  uint16_t qmax = 0,q,l;
  uint16_t b_init_level = mah_to_level(B_INIT);
  #ifdef DEBUG
      if (idmax!=0) {
        printf("%d %d %d %d\n",b,level_to_mah(b),qmax,idmax);
      }
  #endif

  for (b=BATTERY_SAMPLING; b>=0; b--) {
    uint16_t b_mAh = level_to_mah(b);               // convert level b to mhA
    idmax = 0;
    qmax = 0;
    for (t=N_TASKS-1; t>=0; t--) {
      Br = min(b_mAh - tasks[t].c_mAh + E[k], BMAX);
      if (Br >= B_INIT) {
         qmax = tasks[t].q_perc;
         idmax = t+1;
         break;
      }
    }
    Q[k%2][b] = qmax;
    S[k][b] = idmax;
    #ifdef DEBUG
      sprintf(buf,"qmax=%d, idmax=%d\n",qmax,idmax);
      Serial.print(buf);
    #endif
  }


  for (k=K-2; k>=0; k--) {
    #ifdef DEBUG
      sprintf(buf,"------ k=%d ----\n",k);
      Serial.print(buf);
    #endif
    for (b=BATTERY_SAMPLING; b>=0; b--) {
      uint16_t b_mAh = level_to_mah(b);
      qmax = 0, idmax = 0; 
      for (t=N_TASKS-1; t>=0; t--) {  // iterate from the last
        Br = min(b_mAh - tasks[t].c_mAh + E[k], BMAX);
        if (Br >= BMIN) {
            l = mah_to_level(Br);   
            assert(l <= BATTERY_SAMPLING);
            q = Q[(k + 1)%2][l];
            if (q!=0 && (q + tasks[t].q_perc) > qmax) {
              qmax = q + tasks[t].q_perc;
              idmax = t+1;
            }
        }
      }
      Q[k%2][b] = qmax;
      S[k][b] = idmax;
    } 
  }
  #ifdef DEBUG
    printf("init level = %d\n",mah_to_level(B_INIT));
    printf("Q = %d\n",K%2==0?Q[K%2][mah_to_level(B_INIT)]:Q[(K+1)%2][mah_to_level(B_INIT)]);
  #endif
  if (K%2 == 0)
    return Q[K%2][mah_to_level(B_INIT)];
  else
    return Q[(K+1)%2][mah_to_level(B_INIT)];
}



int schedulePenalty(uint16_t E[], float eps)
{
  int8_t   t,idmax,j;
  int16_t  b,Br;
  int16_t   k = K-1;       // start in the last slot
  uint16_t qmax = 0,q,l;
  uint16_t b_init_level = mah_to_level(B_INIT);
  int16_t penalty;        /* ADDED FOR NGCC */
 
  #ifdef DEBUG
      if (idmax!=0) {
        printf("%d %d %d %d\n",b,level_to_mah(b),qmax,idmax);
      }
  #endif

  for (b=BATTERY_SAMPLING; b>=0; b--) {
    uint16_t b_mAh = level_to_mah(b);               // convert level b to mhA
    idmax = 0;
    qmax = 0;
    for (t=N_TASKS-1; t>=0; t--) {
      Br = min(b_mAh - tasks[t].c_mAh + E[k], BMAX);
      if (Br >= B_INIT) {
         qmax = tasks[t].q_perc;
         idmax = t+1;
         break;
      }
    }
    Q[k%2][b] = qmax;
    S[k][b] = idmax;
    #ifdef DEBUG
      sprintf(buf,"qmax=%d, idmax=%d\n",qmax,idmax);
      Serial.print(buf);
    #endif
  }


  for (k=K-2; k>=0; k--) {
    #ifdef DEBUG
      sprintf(buf,"------ k=%d ----\n",k);
      Serial.print(buf);
    #endif
    for (b=BATTERY_SAMPLING; b>=0; b--) {
      uint16_t b_mAh = level_to_mah(b);
      qmax = 0, idmax = 0; 
      for (t=N_TASKS-1; t>=0; t--) {  // iterate from the last
        Br = min(b_mAh - tasks[t].c_mAh + E[k], BMAX);
        if (Br >= BMIN) {
            l = mah_to_level(Br);   
            assert(l <= BATTERY_SAMPLING);
            q = Q[(k + 1)%2][l];
  
/********************************* ADDED NGCC Init *****************************************/
            if (q==0) continue;
            j = S[k+1][l];
            penalty = int(eps * (abs(tasks[t].q_perc - tasks[j].q_perc) - tasks[0].q_perc));
            if (q + tasks[t].q_perc - penalty > qmax){
                qmax = q + tasks[t].q_perc - penalty;
                idmax = t+1;
            }
/********************************* ADDED NGCC End ******************************************/
        }
      }
      Q[k%2][b] = qmax;
      S[k][b] = idmax;
    } 
  }
  #ifdef DEBUG
    printf("init level = %d\n",mah_to_level(B_INIT));
    printf("Q = %d\n",K%2==0?Q[K%2][mah_to_level(B_INIT)]:Q[(K+1)%2][mah_to_level(B_INIT)]);
  #endif
  if (K%2 == 0)
    return Q[K%2][mah_to_level(B_INIT)];
  else
    return Q[(K+1)%2][mah_to_level(B_INIT)];
}




void setup() {
  Serial.begin(115200);
  srand(SEED);
  GenerateTasks();
  InitializeEnergyHarvested();
  PrintParameters();

}

/* Variables for loop */
uint8_t counter = 0, i=0;              // iteration counter
unsigned long t1, t2, t3, t4; 
uint16_t totalEnergyHarvested = 0;
uint16_t optQ;

float eps;                            /* ADDED FOR NGCC */

void loop() {

  if (counter < N_ITERATION) {

    Serial.print(F("it,Energy = "));
    Serial.print(counter);  
    Serial.print(",");
    if (counter != 0)  { update_panel(); }
    totalEnergyHarvested = 0;
    
    for(i=0; i<K; i++) { totalEnergyHarvested += E_s_mAh[i]; }
        Serial.println(totalEnergyHarvested);

    Serial.print(F("E = ["));
    for (i=0; i<K; i++) {
        Serial.print(E_s_mAh[i]);
        Serial.print(i==K-1?"]":",");
    } 
    Serial.println("");

    ClearQS();

    // ***** Scheduling ******
 /*   t1 = millis();
    optQ = schedule(E_s_mAh);
    t2 = millis();
   
    if (optQ != 0) {
      Serial.print(F("Q = "));
      Serial.println(optQ);
      scheduleTasks(E_s_mAh,optQ);
      Serial.print("S = [");
      for(i=0; i<K; i++) {
        Serial.print(NS[i]);
        Serial.print((i==K-1)?"]":",");
      }
      Serial.println("");
    }
    Serial.print(F("Time = "));
    Serial.println(t2-t1);
    ClearQS();
*/

  
    // ***** Scheduling NGCC ******
    t3 = millis();
    eps = 0.2;
    optQ = schedulePenalty(E_s_mAh, eps);
    t4 = millis();
   
    if (optQ != 0) {
      Serial.print(F("Q = "));
      Serial.println(optQ);
      scheduleTasks(E_s_mAh,optQ);
      Serial.print("S = [");
      for(i=0; i<K; i++) {
        Serial.print(NS[i]);
        Serial.print((i==K-1)?"]":",");
      }
      Serial.println("");
    }
    Serial.print(F("Time = "));
    Serial.println(t4-t3);

   
    counter++;
  } else {delay(1000);}
}
