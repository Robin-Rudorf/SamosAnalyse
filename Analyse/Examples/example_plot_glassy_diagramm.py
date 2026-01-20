import random
import sys, os, glob
import pickle as pickle
import copy as cp
import numpy as np
import scipy as sp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as ptch
import matplotlib.lines as lne
from matplotlib.colors import LinearSegmentedColormap


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
                   
import argparse

# Note that these hard-coded paths need to be modified before this script can be used
sys.path.insert(1,'/home/user/samos/analysis/')

topdir_pickle='/home/user/samos/run3_analysis/pickle/'
topdir_python='/home/user/samos/analysis/'

# All the paramters which we have ever considered (fixed systems)
# This will plot Figure 7a, among others
gamval=['0.1']
nuval=['0.1']
v0=['0.01','0.03','0.1','0.2','0.3','0.6']

permult=['2.0','2.2', '2.4','2.6', '2.8','2.9', '3.0','3.1', '3.2', '3.25','3.3','3.35', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9', '4.0', '4.1', '4.2', '4.3']
# Another wrinkle: The 2.5 is for the runs where the time stepping was larger, so that there are 2.5 time units between frames, instead of 1 
# This should have been taken care of in the processing, but there was an error.
# All tmult = 1 for cleanly resimulated data ...
tmult=[1,2.5,1,2.5,1,2.5,1,2.5,1,2.5,2.5,2.5,1,1,1,1,1,1,1,1,1,1,1]
#lineval=['0.0','0.1','0.3','1.0']
lineval=['0.1']
skip=50

#fixed=True
fixed=False
if fixed:
    A0=3.1415
else:
    A0=3.0

# Creating line colors for different line plots
multmap=LinearSegmentedColormap('test',cdict,N=len(permult)) 
vmap=LinearSegmentedColormap('test',cdict,N=len(v0))
linemap=LinearSegmentedColormap('test',cdict,N=len(lineval))
# creating markes as well
mrkr=['o','d','x','>']
lsty=['-',':','--','-.']

				      
## Now we need to look at the glassy things ...

# Beginning with the MSD, which turns out to be not satisfactory, as there are no clear plateau values corresponding to a cage size,
# like one would expect for a particle-based model
# Also, a number of our runs are too short to have satisfactory data here
#for nu in nuval:
        #for line in lineval:
                #for gamma in gamval:
                        #for v in v0:
                                #plt.figure()
                                #for p in range(len(permult)):
                                        #try:
                                                #if fixed:
                                                    #picklefile=topdir_pickle+'glassy_fixed_v'+v+'_nu'+nu+'_gam'+gamma+'_per'+permult[p]+'_line'+line+'.p'
                                                #else:
                                                    #picklefile=topdir_pickle+'glassy_open_v'+v+'_nu'+nu+'_gam'+gamma+'_per'+permult[p]+'_line'+line+'.p'
                                                #print picklefile
                                                #data=pickle.load(open(picklefile, "rb"))
                                                #tplot=data['tplot']
                                                #MSD=data['msd']
                                                ##tplot=np.linspace(0,tmult[p]*len(MSD),len(MSD))
                                                #print len(MSD)
                                                #plt.loglog(tplot,MSD,'-',color=multmap(p),lw=2,label='p_0=' +permult[p])
                                        #except:
                                                #print "Didn't get data"
                                                #pass
                                #plt.xlabel('time')
                                #plt.ylabel('MSD')
                                #plt.legend(loc=2)
                                #plt.title('v0='+v+', nu=' + nu+', gamma='+gamma+', line=' +line)
 
# Move to the Self-Intermediate scattering function to determine glassiness.
# Quite the headscratcher. Maybe the Self-intermediate is easier?
# Yes, it clearly is ...
# Criterion: It's glassy if we stay above 0.5, otherwise it's not
# Define a time scale by the time it reaches 0.5.
for nu in nuval:
        for line in lineval:
                for gamma in gamval:
                        for v in v0:
                                plt.figure()
                                for p in range(len(permult)):
                                        try:
                                                if fixed:
                                                    picklefile=topdir_pickle+'glassy_fixed_v'+v+'_nu'+nu+'_gam'+gamma+'_per'+permult[p]+'_line'+line+'.p'
                                                else:
                                                    picklefile=topdir_pickle+'glassy_open_v'+v+'_nu'+nu+'_gam'+gamma+'_per'+permult[p]+'_line'+line+'.p'
                                                print picklefile
                                                data=pickle.load(open(picklefile, "rb"))
                                                tplot=data['tval']
                                                SelfInt=data['SelfInt']
                                                #tplot=np.linspace(0,tmult[p]*(len(SelfInt)),len(SelfInt))
                                                print len(SelfInt)
                                                plt.semilogx(tplot,SelfInt,'-',color=multmap(p),lw=2,label='p_0=' +permult[p])
                                        except:
                                                print "Didn't get data"
                                                pass
                                plt.xlabel('time')
                                plt.ylabel('Self-Int')
                                plt.legend(loc=1)
                                plt.title('v0='+v+', nu=' + nu+', gamma='+gamma+', line=' +line)
                                
isglassy=np.zeros((len(v0),len(nuval),len(gamval),len(permult),len(lineval)))
taualpha=np.ones((len(v0),len(nuval),len(gamval),len(permult),len(lineval)))
isdata=np.zeros((len(v0),len(nuval),len(gamval),len(permult),len(lineval)))


with open("plot_error.txt", "w") as f:
    f.close()
 

for v in range(len(v0)):
	for nu in range(len(nuval)):
		for gam in range(len(gamval)):
			for p in range(len(permult)):
				for l in range(len(lineval)):
				      try:
                                          if fixed:
                                              picklefile=topdir_pickle+'glassy_fixed_v'+v0[v]+'_nu'+nuval[nu]+'_gam'+gamval[gam]+'_per'+permult[p]+'_line'+lineval[l]+'.p'
                                          else:
                                              picklefile=topdir_pickle+'glassy_open_v'+v0[v]+'_nu'+nuval[nu]+'_gam'+gamval[gam]+'_per'+permult[p]+'_line'+lineval[l]+'.p'
					  
					  print picklefile
					  data=pickle.load(open(picklefile, "rb"))
                                          tplot=data['tval']
                                          SelfInt=data['SelfInt']
                                          print len(tplot)
                                          if len(tplot)>26:
                                                isdata[v,nu,gam,p,l]=1
                                                hmm = [index for index,value in enumerate(SelfInt) if value<0.5]
                                                if len(hmm)>0:
                                                        idx=min(hmm)
                                                        taualpha[v,nu,gam,p,l]=tplot[idx]
                                                else: 
                                                        # Take into account how long this thing has actually run ...
                                                        # Taualpha is set to the maximum runtime of the actual simulation in this case
                                                        if p<12:
                                                                taualpha[v,nu,gam,p,l]=6250
                                                                isglassy[v,nu,gam,p,l]=1
                                                        else:
                                                                taualpha[v,nu,gam,p,l]=1000
				      except:
					  with open("plot_error.txt", "a") as f:
					    f.write('glassy_open_v'+v0[v]+'_nu'+nuval[nu]+'_gam'+gamval[gam]+'_per'+permult[p]+'_line'+lineval[l]+'.p\n')
					    f.close()
					  #pass

# Line plot of the results
# Careful, this is labeled by permult, and not the actual p_0
for nu in range(len(nuval)):
        for gam in range(len(gamval)):
                plt.figure()
                for l in range(len(lineval)):
                        for v in range(len(v0)):
                                idxs= [index for index,value in enumerate(isdata[v,nu,gam,:,l]) if value>0]
                                print idxs
                                xval=2*np.array(permult).astype(float)/np.sqrt(A0)
                                #xval=np.array(permult).astype(float)
                                plt.semilogy(xval[idxs],taualpha[v,nu,gam,idxs,l],marker=mrkr[l],linestyle=lsty[l],lw=2,color=vmap(v),label='v0=' +v0[v] )
                plt.xlabel('p0')
                plt.ylabel('Alpha-relaxation time')
                plt.title('Noise ' +nuval[nu]+', gamma ' + gamval[gam])

# Plot phase diagrams of the glassy time scale, as in Figure 7 a,b,c in the paper
# A lot of bespoke wrangling with the placement of labels and ticks here due to
# 1) conversion from permult to p0: 
# p_0 = 2*permult/sqrt(A_0) = 1.1284 * permult for fixed systems
# p_0 = 2*permult/sqrt(A_0) = 1.1547 * permult for open systems
# 2) The default of pcolor is not to centre the boxes on the coordinates, but to place the box edges there
permult.append('4.4')
v0.append('0.9')
if fixed==False:
        actual=np.array([ 2.30940108,  2.54034118,  2.77128129,  3.0022214 ,  3.23316151,
                3.34863156,  3.46410162,  3.57957167,  3.69504172,  3.75277675,
                3.81051178,  3.8682468 ,  3.92598183,  4.04145188,  4.15692194,
                4.27239199,  4.38786205,  4.5033321 ,  4.61880215,  4.73427221,
                4.84974226,  4.96521232,  5.08068237])
else:
        actual=np.array([ 2.25679161,  2.48247078,  2.70814994,  2.9338291 ,  3.15950826,
        3.27234784,  3.38518742,  3.498027  ,  3.61086658,  3.66728637,
        3.72370616,  3.78012595,  3.83654574,  3.94938532,  4.0622249 ,
        4.17506449,  4.28790407,  4.40074365,  4.51358323,  4.62642281,
        4.73926239,  4.85210197,  4.96494155])
myactual=0.5*(actual[0:(len(actual)-1)]+actual[1:])
xtick0=[2.5,3.0,3.5,4.0,4.5,5.0]
xtick1=[2.6,3.1,3.6,4.1,4.6,5.1]
ytick1=[0.01,0.03,0.1,0.2,0.3,0.6]
ytick0=[np.log10(0.015),np.log10(0.05),np.log10(0.17),np.log10(0.31),np.log10(0.45),np.log10(0.75)]
for nu in range(len(nuval)):
        for gam in range(len(gamval)):
                for l in range(len(lineval)):
                        plt.figure()
                        xval=2*np.array(permult).astype(float)/np.sqrt(A0)
                        yval=np.log10(np.array(v0).astype(float))
                        plt.pcolor(xval,yval,np.log10(taualpha[:,nu,gam,:,l]),cmap='Reds',vmin=0.5, vmax=3.6)
                        for u in range(len(yval)-1):
                            isd=[index for index,value in enumerate(isdata[u,nu,gam,:,l]) if value==1]
                            print isd
                            plt.plot(myactual[isd],ytick0[u]*myactual[isd]/myactual[isd],'ok',markeredgecolor='k')
                        #plt.pcolor(taualpha[:,nu,gam,:,l])
                        plt.colorbar()
                        plt.xticks(xtick1,xtick0,fontsize=20)
                        plt.yticks(ytick0,ytick1,fontsize=20)
                        #plt.xlim(2.3,5.08)
                        plt.xlim(2.256,4.5)
                        #plt.xlim(2.256,4.96)
                        plt.ylim(-2,np.log10(0.9))
                        plt.title('Noise ' +nuval[nu]+', gamma ' + gamval[gam]+', line ' + lineval[l])
                        

                        
#plt.show()
plt.savefig('diagramm.png')
		







