#!/usr/bin/env python3

import sys, os, glob
import pickle as pickle
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import csv

# Changing system parameters for plotting optics
matplotlib.rcParams['text.usetex'] = 'false'
matplotlib.rcParams['lines.linewidth'] = 2
matplotlib.rcParams['axes.linewidth'] = 2
matplotlib.rcParams['xtick.major.size'] = 8
matplotlib.rcParams['ytick.major.size'] = 8
matplotlib.rcParams['font.size']=16.0
matplotlib.rcParams['legend.fontsize']=14.0
# Color dictionary for line graphs
cdict = {'red':   [(0.0,  0.0, 0.5),
                   (0.35,  1.0, 0.75),
                   (0.45,  0.75, 0.0),
                   (1.0,  0.0, 0.0)],

         'green': [(0.0,  0.0, 0.0),
                   (0.35,  0.0, 0.5),
                   (0.5, 1.0, 1.0),
                   (0.8,  0.5, 0.0),
                   (1.0,  0.0, 0.0)],

         'blue':  [(0.0,  0.0, 0.0),
                   (0.5,  0.0, 0.0),
                   (0.7, 0.5, 1.0),
                   (1.0,  0.25, 0.0)]}



# Note that these hard-coded paths need to be modified before this script can be used
#sys.path.insert(1,'@python_utils@')

topdir_pickle='analyse/pickle'


cc_val=[]
rand_val=[]
tau_val=[]
v_val=[]
k_val=[]
nu_val=[]
gamma_val=[]
permult_val=[]
line_val=[]

with open(topdir_pickle+"/pickle.csv") as f:
    csv_data=csv.reader(f,delimiter=",")
    for row in csv_data:
        try:
            cc_val.index(row[0])
        except ValueError:
            cc_val.append(row[0])
        try:
            rand_val.index(row[1])
        except ValueError:
            rand_val.append(row[1])
        try:
            tau_val.index(row[2])
        except ValueError:
            tau_val.append(row[2])
        try:
            v_val.index(row[3])
        except ValueError:
            v_val.append(row[3])
        try:
            k_val.index(row[4])
        except ValueError:
            k_val.append(row[4])
        try:
            nu_val.index(row[5])
        except ValueError:
            nu_val.append(row[5])
        try:
            gamma_val.index(row[6])
        except ValueError:
            gamma_val.append(row[6])
        try:
            permult_val.index(row[7])
        except ValueError:
            permult_val.append(row[7])
        try:
            line_val.index(row[8])
        except ValueError:
            line_val.append(row[8])

cc_val.sort()
rand_val.sort()
tau_val.sort()
v_val.sort()
k_val.sort()
nu_val.sort()
gamma_val.sort()
permult_val.sort()
line_val.sort()

print("cc: "+str(cc_val))
print("rand: "+str(rand_val))
print("tau: "+str(tau_val))
print("v: "+str(v_val))
print("k: "+str(k_val))
print("nu: "+str(nu_val))
print("gamma: "+str(gamma_val))
print("permult: "+str(permult_val))
print("line: "+str(line_val))



# All the paramters which we have ever considered (fixed systems)
# This will plot Figure 7a, among others
#gamval=gamma_val
#nuval=nu_val
#v0=v_val
#permult=permult_val
#lineval=line_val

A0=3.0

# Creating line colors for different line plots
multmap=LinearSegmentedColormap('test',cdict,N=len(permult_val)) 
vmap=LinearSegmentedColormap('test',cdict,N=len(v_val))
linemap=LinearSegmentedColormap('test',cdict,N=len(line_val))
# creating markes as well
mrkr=['o','d','x','>']
lsty=['-',':','--','-.']

## Now we need to look at the glassy things ...

# Move to the Self-Intermediate scattering function to determine glassiness.
# Quite the headscratcher. Maybe the Self-intermediate is easier?
# Yes, it clearly is ...
# Criterion: It's glassy if we stay above 0.5, otherwise it's not
# Define a time scale by the time it reaches 0.5.
for cc in cc_val:
    for rand in rand_val:
        for tau in tau_val:
            for k in k_val:
                for nu in nu_val:
                    for line in line_val:
                        for gamma in gamma_val:
                            for v in v_val:
                                plt.figure(figsize=(11,7))
                                # Group by permult
                                for permult_idx in range(len(permult_val)):
                                        try:
                                                picklefile=topdir_pickle+'/cc_'+cc+';rand_'+rand+';tau_'+tau+';v0_'+v+';k_1.0;nu_'+nu+';gamma_'+gamma+';permult_'+permult_val[permult_idx]+';line_'+line+'.p'
                                                #print(picklefile)
                                                data=pickle.load(open(picklefile, "rb"))
                                                #print(data)
                                                tplot=data['tval']
                                                SelfInt=data['SelfInt']
                                                #print("Len(SelfInt): "+str(len(SelfInt)))

                                                plt.semilogx(tplot,SelfInt, linewidth=1.5, label=permult_val[permult_idx])

                                        except:
                                                print("Didn't get data "+picklefile)
                                                pass
                                plt.legend(title="Permult",bbox_to_anchor=(1.02,1), loc="upper left", frameon=True)
                                plt.xlabel('time')
                                plt.ylabel('Self-Int')
                                plt.title('cc='+cc+', rand='+rand+', tau='+tau+', k='+k+', v0='+v+', nu='+ nu+', gamma='+gamma+', line='+line, fontsize=10)
                                plt.tight_layout()
                                plt.savefig('cc_'+cc+';rand_'+rand+';tau_'+tau+';v0_'+v+';k_'+k+';nu_'+nu+';gamma_'+gamma+';line_'+line+'.png', dpi=200)
                                plt.close()


#####################################################################################



isglassy=np.zeros((len(cc_val),len(rand_val),len(tau_val),len(k_val),len(v_val),len(nu_val),len(gamma_val),len(permult_val),len(line_val)))
taualpha=np.ones((len(cc_val),len(rand_val),len(tau_val),len(k_val),len(v_val),len(nu_val),len(gamma_val),len(permult_val),len(line_val)))
isdata=np.zeros((len(cc_val),len(rand_val),len(tau_val),len(k_val),len(v_val),len(nu_val),len(gamma_val),len(permult_val),len(line_val)))





with open("plot_error.txt", "w") as f:
    f.close()


for cc in range(len(cc_val)):
    for rand in range(len(rand_val)):
        for tau in range(len(tau_val)):
            for k in range(len(k_val)):
                for v in range(len(v_val)):
                    for nu in range(len(nu_val)):
                        for gam in range(len(gamma_val)):
                            for p in range(len(permult_val)):
                                for l in range(len(line_val)):
                                    try:
                                        picklefile=topdir_pickle+'/cc_'+cc_val[cc]+';rand_'+rand_val[rand]+';tau_'+tau_val[tau]+';v0_'+v_val[v]+';k_'+k_val[k]+';nu_'+nu_val[nu]+';gamma_'+gamma_val[gam]+';permult_'+permult_val[p]+';line_'+line_val[l]+'.p'

                                        #print(picklefile)
                                        data=pickle.load(open(picklefile, "rb"))
                                        tplot=data['tval']
                                        SelfInt=data['SelfInt']
                                        #print("Len(tplot): "+str(len(tplot)))
                                        if len(tplot)>26:
                                            isdata[cc,rand,tau,k,v,nu,gam,p,l]=1
                                            hmm = [index for index,value in enumerate(SelfInt) if value<0.5]
                                            if len(hmm)>0:
                                                idx=min(hmm)
                                                taualpha[cc,rand,tau,k,v,nu,gam,p,l]=tplot[idx]
                                            else:
                                                # Take into account how long this thing has actually run ...
                                                # Taualpha is set to the maximum runtime of the actual simulation in this case
                                                if p<12:
                                                    taualpha[cc,rand,tau,k,v,nu,gam,p,l]=2500 #6250
                                                    isglassy[cc,rand,tau,k,v,nu,gam,p,l]=1
                                                else:
                                                    taualpha[cc,rand,tau,k,v,nu,gam,p,l]=1000
                                    except:
                                        with open("plot_error.txt", "a") as f:
                                            f.write(cc_val[cc]+'_rand'+rand_val[rand]+'_tau'+tau_val[tau]+'_k'+k_val[k]+'_v'+v_val[v]+'_nu'+nu_val[nu]+'_gam'+gamma_val[gam]+'_per'+permult_val[p]+'_line'+line_val[l]+'.p\n')
                                            f.close()

# ---------------------------------------------------------------------------------



# Line plot of the results
# Careful, this is labeled by permult, and not the actual p_0
for cc in range(len(cc_val)):
    for rand in range(len(rand_val)):
        for tau in range(len(tau_val)):
            for k in range(len(k_val)):
                for nu in range(len(nu_val)):
                    for gam in range(len(gamma_val)):
                        for l in range(len(line_val)):
                            plt.figure(figsize=(11,7))
                            for v in range(len(v_val)):
                                idxs= [index for index,value in enumerate(isdata[cc,rand,tau,k,v,nu,gam,:,l]) if value>0]
                                xval=2*np.array(permult_val).astype(float)/np.sqrt(A0)
                                #xval=np.array(permult).astype(float)
                                #plt.semilogy(xval[idxs],taualpha[cc,rand,tau,k,v,nu,gam,idxs,l],marker=mrkr[l],linestyle=lsty[l],lw=1.5,color=vmap(v),label='v0=' +v_val[v] )
                                plt.semilogy(xval[idxs],taualpha[cc,rand,tau,k,v,nu,gam,idxs,l],marker="o",lw=1.5,label=v_val[v] )
                        plt.xlabel('p0')
                        plt.ylabel('Alpha-relaxation time')
                        plt.legend(title="v0",bbox_to_anchor=(1.02,1), loc="upper left", frameon=True)
                        plt.title('cc:'+cc_val[cc]+', rand:'+rand_val[rand]+', tau:'+tau_val[tau]+', k:'+k_val[k]+', nu: '+nu_val[nu]+', gamma:'+gamma_val[gam]+',line:'+line_val[l],fontsize=10)
                        plt.locator_params(axis='x', nbins=15)
                        plt.tight_layout()
                        plt.savefig('ART1_cc_'+cc_val[cc]+';rand_'+rand_val[rand]+';tau_'+tau_val[tau]+';k_'+k_val[k]+';nu_'+nu_val[nu]+';gamma_'+gamma_val[gam]+';line_'+line_val[l]+'.png')

# ---------------------------------------------------------------------------------

# Plot phase diagrams of the glassy time scale, as in Figure 7 a,b,c in the paper
# A lot of bespoke wrangling with the placement of labels and ticks here due to
# 1) conversion from permult to p0: 
# p_0 = 2*permult/sqrt(A_0) = 1.1284 * permult for fixed systems
# p_0 = 2*permult/sqrt(A_0) = 1.1547 * permult for open systems
# 2) The default of pcolor is not to centre the boxes on the coordinates, but to place the box edges there

permult_val.append('4.4')
#permult_val.append(str(float(max(permult_val))*1.1))

#actual=np.array([ 2.30940108,  2.54034118,  2.77128129,  3.0022214 ,  3.23316151,
#                3.34863156,  3.46410162,  3.57957167,  3.69504172,  3.75277675,
#                3.81051178,  3.8682468 ,  3.92598183,  4.04145188,  4.15692194,
#                4.27239199,  4.38786205,  4.5033321 ,  4.61880215,  4.73427221,
#                4.84974226,  4.96521232,  5.08068237])
actual_tmp=[]
for per in permult_val:
    actual_tmp.append(2*float(per)/np.sqrt(A0))
actual=np.array(actual_tmp)


myactual=0.5*(actual[0:(len(actual)-1)]+actual[1:])

xtick0=[2.6,3.1,3.6,4.1,4.6,5.1]
xtick1=[2.5,3.0,3.5,4.0,4.5,5.0]

#ytick1=[0.01,0.03,0.1,0.2,0.3,0.6]
ytick1=[]
for yt in v_val:
    ytick1.append(float(yt))

#ytick0=[np.log10(0.015),np.log10(0.05),np.log10(0.17),np.log10(0.31),np.log10(0.45),np.log10(0.75)]
ytick0=[]
for yt in v_val:
    ytick0.append(np.log10(float(yt)*1.3))

#v_val.append(str(float(max(v_val))*1.5))
v_val.append('0.6')
#v_val.append('0.9')

for cc in range(len(cc_val)):
    for rand in range(len(rand_val)):
        for tau in range(len(tau_val)):
            for k in range(len(k_val)):
                for nu in range(len(nu_val)):
                    for gam in range(len(gamma_val)):
                        for l in range(len(line_val)):
                            plt.figure(figsize=(11,7))
                            xval=2*np.array(permult_val).astype(float)/np.sqrt(A0)
                            yval=np.log10(np.array(v_val).astype(float))
                            plt.pcolor(xval,yval,np.log10(taualpha[cc,rand,tau,k,:,nu,gam,:,l]),cmap='Reds',vmin=0.5, vmax=3.6)
                            for u in range(len(yval)-1):
                                isd=[index for index,value in enumerate(isdata[cc,rand,tau,k,u,nu,gam,:,l]) if value==1]
                                plt.plot(myactual[isd],ytick0[u]*myactual[isd]/myactual[isd],'ok',markeredgecolor='k')
                            #plt.pcolor(taualpha[:,nu,gam,:,l])
                            plt.colorbar()
                            plt.xticks(xtick0,xtick1,fontsize=20)
                            plt.yticks(ytick0,ytick1,fontsize=20)
                            ##plt.xlim(2.3,5.08)
                            plt.xlim(2.256,4.5)
                            ##plt.xlim(2.256,4.96)
                            plt.ylim(-2,np.log10(0.9))
                            plt.title('cc:'+cc_val[cc]+', rand:'+rand_val[rand]+', tau:'+tau_val[tau]+', k:'+k_val[k]+', nu: '+nu_val[nu]+', gamma:'+gamma_val[gam]+', line:'+ line_val[l],fontsize=10)
                            #plt.tight_layout()
                            plt.savefig('ART2_cc_'+cc_val[cc]+';rand_'+rand_val[rand]+';tau_'+tau_val[tau]+';k_'+k_val[k]+';nu_'+nu_val[nu]+';gamma_'+gamma_val[gam]+';line;'+ line_val[l]+'.png')










