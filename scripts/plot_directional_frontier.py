"""Plot analytic feasibility/testability regions, not simulated observations."""
from pathlib import Path
import shutil

import numpy as np


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    root = Path(__file__).resolve().parents[1]
    with matplotlib.rc_context():
        matplotlib.rcdefaults()
        plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
        second = np.linspace(0.,1.,1201)
        feasible_top = np.sqrt(second); utility_boundary = second/2
        fig,ax = plt.subplots(figsize=(6.2,4.1))
        ax.fill_between(second,0,utility_boundary,color='0.75',alpha=.35)
        ax.fill_between(second,utility_boundary,np.minimum(.5,feasible_top),
                        color='C1',alpha=.35)
        ax.fill_between(second,.5,feasible_top,where=feasible_top>=.5,
                        interpolate=True,color='C2',alpha=.3)
        ax.plot(second,feasible_top,color='0.35',linewidth=1)
        ax.plot(second,utility_boundary,color='C1',linewidth=1)
        ax.axhline(.5,color='0.25',linestyle='--',linewidth=1.1)
        ax.scatter([.04,.64],[.2,.8],color='black',s=21,zorder=4)
        ax.annotate('A',(.04,.2),xytext=(6,1),textcoords='offset points')
        ax.annotate('B',(.64,.8),xytext=(6,1),textcoords='offset points')
        ax.text(.10,.83,'Not feasible:\n'+r'$(\mathbb{E}r)^2>\mathbb{E}r^2$',fontsize=9,color='0.35')
        ax.text(.98,.515,r'$\mu=\gamma K_2/2$',ha='right',fontsize=9,color='0.25')
        ax.text(.98,.43,r'$\mathbb{E}U=0$',ha='right',fontsize=9,color='C1',rotation=17)
        ax.set(xlim=(0,1),ylim=(0,1.02),xlabel=r'Actual second return moment $\mathbb{E}r^2$',
               ylabel=r'Mean return $\mu=\mathbb{E}r$',title=r'Fixed ENTRY: known cap $K_2=1$, risk aversion $\gamma=1$')
        handles=[Patch(facecolor='C2',alpha=.3,label='Eventual power one is possible'),
                 Patch(facecolor='C1',alpha=.35,label='Positive utility; every uniform level test has power at most size'),
                 Patch(facecolor='0.75',alpha=.35,label='Nonpositive utility')]
        ax.legend(handles=handles,loc='upper left',bbox_to_anchor=(0,-.19),fontsize=9,
                  frameon=False,borderaxespad=0)
        fig.subplots_adjust(bottom=.32,left=.12,right=.98,top=.89)
        destination=root/'paper/figures/directional_frontier.png'
        fig.savefig(destination,dpi=180);plt.close(fig)
    shutil.copyfile(destination,root/'reports/directional_frontier.png')
    print(destination)


if __name__ == '__main__':
    main()
