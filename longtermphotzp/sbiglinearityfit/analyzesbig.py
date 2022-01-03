import datetime
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
plt.style.use('ggplot')
matplotlib.rcParams['savefig.dpi'] = 300
matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
import longtermphotzp
from longtermphotzp.longtermphotzp import dateformat
from longtermphotzp.sbiglinearityfit.sbiglinedbinterface import sbiglininterface
starttime = datetime.datetime(2016, 1, 1)

endtime = datetime.datetime.utcnow().replace(day=28) + datetime.timedelta(days=31 + 4)
endtime.replace(day=1)

def analysecamera (camera, storageengine):

    records = storageengine.readRecords(camera = camera)
    records = records[( records['nstars']>=10) & (records['photslopebefore']!= records['photslopeafter'])]

    plt.figure ()
    plt.title (f"{camera} fit parameter z")
    plt.plot (records ['dateobs'], records['fit_z'], '.')
    plt.xlabel ("DATE-OBS")
    plt.ylim([0,1000])
    dateformat(starttime, endtime)
    plt.savefig (f"{camera}_timeline_2z.png")
    plt.close()

    plt.figure ()
    plt.title (f"{camera} fit parameter k")
    plt.plot (records ['dateobs'], records['fit_k'], '.')
    dateformat(starttime, endtime)
    plt.xlabel ("DATE-OBS")
    plt.ylim([0.9,2])
    plt.savefig (f"{camera}_timeline_1k.png")
    plt.close()

    plt.figure ()
    plt.title (f"{camera} Pre-correction slope in photzp")
    plt.plot (records ['dateobs'], records['photslopebefore'], '.')
    dateformat(starttime, endtime)
    plt.xlabel ("DATE-OBS")
    plt.ylim([-0.01,0.3])
    plt.ylabel("photzp slope [mag/mag]")
    plt.savefig (f"{camera}_timeline_0photslopebefore.png")
    plt.close()

    plt.figure ()
    plt.title (f"{camera} Background level [e-]")
    plt.semilogy (records ['dateobs'], records['background'], '.')
    dateformat(starttime, endtime)
    plt.xlabel ("DATE-OBS")
    plt.ylim([0,2000])
    plt.ylabel("L1MEDIAN Beckground [e-]")
    plt.savefig (f"{camera}_timeline_4background.png")
    plt.close()

    plt.figure ()
    plt.title (f"{camera} fit parameter z")
    plt.xlabel ("background level [e-]")
    plt.xlim ([0,500])
    plt.ylim([0,1000])
    plt.plot (records ['background'], records['fit_z'], '.')
    plt.legend()
    plt.savefig (f"{camera}_background_2z.png")
    plt.close()

    plt.figure ()
    plt.xlabel ("background level [e-]")
    plt.title (f"{camera} fit parameter k")
    plt.semilogx(records ['background'], records['fit_k'], '.')
    plt.xlim([0,2000])
    plt.ylim([0.9,2])
    plt.savefig (f"{camera}_background_1k.png")
    plt.close()


    plt.figure ()
    plt.xlabel ("background level [e-]")
    plt.title (f"{camera} pre correction slope in photzp")
    plt.semilogx (records ['background'], records['photslopebefore'], '.')
    plt.xlim([0,2000])
    plt.ylim([-0.01,0.3])
    plt.savefig (f"{camera}_background_0photslope.png")
    plt.close()


    plt.figure ()
    plt.xlabel ("background level [e-]")
    plt.title (f"{camera} post correction slope in photzp")
    plt.semilogx (records ['background'], records['photslopeafter'], '.')
    plt.xlim([0,2000])
    plt.ylim([-0.01,0.3])
    plt.savefig (f"{camera}_background_photslopeafter.png")
    plt.close()



if __name__ == '__main__':
    storageengine = sbiglininterface(os.environ['DATABASE'])

    analysecamera ('kb23', storageengine)
    analysecamera ('kb26', storageengine)
    analysecamera ('kb95', storageengine)
    analysecamera ('kb96', storageengine)
    analysecamera ('kb97', storageengine)
    analysecamera ('kb55', storageengine)
    storageengine.close()
