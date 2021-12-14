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

    change = datetime.datetime(2018, 6, 1)

    before = records['dateobs'] < change
    after = records['dateobs'] > change

    plt.figure ()
    plt.title (f"{camera} fit parameter z")
    plt.plot (records ['dateobs'], records['fit_z'], '.')
    plt.xlabel ("DATE-OBS")
    plt.ylim([0,1000])
    dateformat(starttime, endtime)
    plt.savefig (f"{camera}_timeline_z.png")


    plt.figure ()
    plt.title (f"{camera} fit parameter k")
    plt.plot (records ['dateobs'], records['fit_k'], '.')
    dateformat(starttime, endtime)
    plt.xlabel ("DATE-OBS")
    plt.ylim([0.9,2])
    plt.savefig (f"{camera}_timeline_k.png")


    plt.figure ()
    plt.title (f"{camera} fit parameter z")
    plt.xlabel ("background level [e-]")
    plt.xlim ([0,2000])
    plt.ylim([0,1000])
    plt.plot (records ['background'][before], records['fit_z'][before], '.', label='before')
    plt.plot (records ['background'][after], records['fit_z'][after], '.', label='after')
    plt.legend()
    plt.savefig (f"{camera}_background_z.png")

    plt.figure ()
    plt.xlabel ("background level [e-]")
    plt.title (f"{camera} fit parameter k")
    plt.plot (records ['background'][before], records['fit_k'][before], '.', label='before')
    plt.plot (records ['background'][after], records['fit_k'][after], '.', label='after')
    plt.legend()
    plt.xlim([0,2000])
    plt.ylim([0.9,2])
    plt.savefig (f"{camera}_background_k.png")
    plt.close()








if __name__ == '__main__':
    storageengine = sbiglininterface(os.environ['DATABASE'])
    analysecamera ('kb95', storageengine)