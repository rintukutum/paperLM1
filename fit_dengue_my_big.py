#
# Multi-year fit of influenza epidemics
#
import pyximport;

pyximport.install(pyimport=False)
from BIP.Bayes.Melding import FitModel
from scipy.integrate import odeint
from scipy.interpolate import interp1d
import scipy.stats as st
import numpy as np
import pylab as P
import copy
from collections import defaultdict
import datetime
import sys
import pandas as pd


beta = 1.0  # Transmission coefficient
b1 = 19.9
b0 = 1.5  # low beta during winters
eta = .0  # infectivity of asymptomatic infections relative to clinical ones. FIXED
epsilon = 2.8  # latency rate
mu = 0  # nat/mortality rate

tau = 1  # recovery rate. FIXED

N = 1  # Population of Rio


#~ Ss = {0: s0, 1: s1, 2: s2}  # Multiple Ss map


# Initial conditions
inits = np.array([1, 0.001, 0.0])  # initial values for state variables.

def model(theta):
    # setting parameters
    s0, s1, s2, s3, s4, s5, s6, s7, s8, s9 = theta
    Ss = {0: s0, 1: s1, 2: s2, 3: s3, 4: s4, 5: s5, 6: s6, 7: s7, 8: s8, 9: s9}  # Multiple Ss map

    # ~ b1=19.9
    def sir(y, t):
        '''ODE model'''
        S, I, R = y
        
        beta = 0 if t > 728 else iRt(t) * tau#(Ss[ycode[int(t)]])

        #~ if (calc_R0s()<1.1).any():
        #~ print "flat"
        lamb = (beta * I * S)
        return [-lamb,  #dS/dt
                lamb - tau * I,  #dI/dt
                tau * I,  #dR/dt
        ]

    Y = np.zeros((wl, 3))
    # Initial conditions

    for i in range(len(Ss)):
        t0 = t0s[i]
        tf = tfs[i]
        #print t0,tf
        if i>0:
            #~ inits[1] = Y[t0-1,1]
            #~ print inits
            inits[1] = dt['I'][t0-1] if N-Ss[i] > dt['I'][t0-1] else N-Ss[i]
        inits[0] = Ss[i];  # Define S0
        inits[-1] = N - sum(inits[:2])  # Define R(0)
        Y[t0:tf, :] = odeint(sir, inits, np.arange(t0, tf, 1))  #,tcrit=tcrit)
        #inits = Y[-1, :]

    return Y


def prepdata(fname, sday=0, eday=None, mao=7):
    """
    Prepare the data for the analysis.

    Parameters:
    file: path to data
    sday: Starting day of the inference
    eday: final day
    mao: Moving average's Order
    """
    data = pd.read_csv(fname, header=0, delimiter=',', skiprows=[1, 2, 3], parse_dates=True)

    dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in data.start]
    sday = sday  # starting day for the fitting
    eday = len(df) if eday is None else eday
    # print data.dtype.names
    incidence = data.cases[sday:eday]  # daily incidence
    # Converting incidence to Prevalence
    dur = 1. / tau  # infectious period
    rawprev = np.convolve(incidence, np.ones(dur), 'same')
    rawprev /= 6e6

    # P.plot(dates, incidence, label='Incidence')
    # P.plot(dates, rawprev, label='Prevalence')
    # P.setp(P.gca().xaxis.get_majorticklabels(), rotation=45)
    # P.grid()
    # P.legend()
    # P.figure()
    # P.plot(dates, data.Rt, label=r'$R_t$')
    # P.plot(dates, data.lwr, 'r-.')
    # P.plot(dates, data.upr, 'r-.')
    # P.setp(P.gca().xaxis.get_majorticklabels(), rotation=45)
    # P.show()
    # Doing moving average of order mao
    if mao > 1:
        sw = np.ones(mao, dtype=float) / mao  #smoothing window
        prev = np.convolve(rawprev, sw, 'same')  #Smoothing data (ma)
    else:
        prev = rawprev
    # sw = np.ones(6, dtype=float) / 6  #smoothing window
    # rt_smooth = np.convolve(data.Rt2, sw, 'same')

    d = {'time': dates, 'I': np.nan_to_num(prev), 'Rt': data.Rt2}
    return d

# TODO: Fix this based on the actual dates
def beta_step(timeline):
    """
    Returns the date ranges where beta should be high, i.e., during summers.
    """
    bstep = np.zeros(len(timeline) + 200)
    for i, d in enumerate(timeline):
        if d.year == 2009:  # In 2009 h1n1 started in the summer
            if d.month != 6:
                bstep[i] = 1
        else:
            if d.month < 7 or d.month > 8:
                bstep[i] = 1
    return np.array(bstep)


def s_index(bstep):
    si = np.zeros(len(bstep))
    s = 0
    for i, b in enumerate(bstep):
        if i == 0: continue
        if b and not bstep[i - 1]:
            s += b
            si[i] = s
    return si

# # running the analysys
if __name__ == "__main__":
    dt = prepdata('aux/data_Rt_dengue_big.csv', 0, 728, 1)
    modname = "Dengue_S0_big"
    # print dt['I'][:,1]

    bstep = beta_step(dt['time'])
    #~ ycode = year_code(dt['time'])
    sindex = s_index(bstep)
    tcrit = [i for i in xrange(len(dt['time'])) if i]
    # Defining start and end of the simulations
    t0s = [0,  # Start of the 1996 epidemic
           dt['time'].index(datetime.datetime(1997, 12, 15)),  # Start of the 1998 epidemic
           dt['time'].index(datetime.datetime(1998, 12, 21)),  # Start of the 1999 epidemic
           dt['time'].index(datetime.datetime(1999, 12, 13)),  # Start of the 2000 epidemic
           dt['time'].index(datetime.datetime(2000, 12, 18)),  # Start of the 2001 epidemic
           dt['time'].index(datetime.datetime(2001, 9, 10)),  # Start of the 2002 epidemic
           dt['time'].index(datetime.datetime(2005, 8, 15)),  # Start of the 2006 epidemic
           dt['time'].index(datetime.datetime(2006, 9, 25)),  # Start of the 2007 epidemic
           dt['time'].index(datetime.datetime(2007, 8, 20)),  # Start of the 2008 epidemic
           dt['time'].index(datetime.datetime(2008, 9, 1)),  # Start of the 2009 epidemic
    ]
    tfs = t0s[1:] + [len(dt['time'])]
    print tfs
    # Interpolated Rt
    iRt = interp1d(np.arange(dt['Rt'].size), np.array(dt['Rt']), kind='cubic', bounds_error=False, fill_value=0)

    P.plot(dt['Rt'],'-*')
    P.plot(np.arange(0,728,.2),[iRt(t) for t in np.arange(0, 728, .2)])
    #print type(dt['Rt'])
    #print [iRt(t) for t in np.arange(0, 728, .2)]

    #~ tfs = np.array(tfs)-1
    #~ print len(sindex), len(dt['I']), len(dt['time'])
    #~ print t0s,tfs
    #~ P.figure()
    #~ P.gca().xaxis_date()
    #~ P.plot(dt['time'],dt['I'],'*-')
    #~ P.plot(dt['time'],dt['I'][:,1],'*-')
    #~ P.plot(dt['time'],bstep[:len(dt['time'])],'-*', label='bstep')
    #~ P.plot(dt['time'],ycode[:len(dt['time'])],'-+', label='ycode')
    #~ P.plot(dt['time'],.001*sindex[:len(dt['time'])],'-v', label='sindex')
    #~ P.legend()
    #~ P.gcf().autofmt_xdate()
    #~ P.show()

    tnames = ['s_{}'.format(i) for i in range(len(t0s))]
    #~ print tnames
    nt = len(tnames)
    pnames = ['S', 'I', 'R']
    nph = len(pnames)
    wl = dt['I'].shape[0]  #window length
    nw = len(dt['time']) / wl  #number of windows
    tf = wl * nw  #total duration of simulation
    inits[1] = dt['I'][0]
    print inits
    #~ print calc_R0s()
    y = model([.9999*N]*nt)
    #print y
    P.figure()
    P.plot(dt['I'], '*')
    P.plot(y[:, 1])
    P.legend([pnames[1]])
    P.show()
    #Priors and limits for all countries
    tpars = [(2, 1)] * nt
    tlims = [(0, 1)] * nt

    F = FitModel(5000, model, inits, tf, tnames, pnames,
                 wl, nw, verbose=1, burnin=2000, constraints=[])
    F.set_priors(tdists=nt * [st.beta],
                 tpars=tpars,
                 tlims=tlims,
                 pdists=[st.beta] * nph, ppars=[(1, 1)] * nph, plims=[(0, 1)] * nph)

    F.run(dt, 'DREAM', likvar=1e-6, pool=False, ew=0, adjinits=False, dbname=modname, monitor=['I', 'S'])
    #~ print F.AIC, F.BIC, F.DIC
    #print F.optimize(data=dt,p0=[s0,s1,s2], optimizer='scipy',tol=1e-55, verbose=1, plot=1)
    F.plot_results(['S', 'I'], dbname=modname, savefigs=1)
