"""Compose the original stereo prologue loops. Requires NumPy, SciPy, soundfile and ffmpeg."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[1]
RATE=48000
OVERLAP=2
MASTERS=ROOT/"assets/audio/ambience-prologue"
RUNTIME=ROOT/"game/assets/audio/ambience-prologue"
ROLES={"p_veyr":("Veyr","Wind across the gallery and two answering tower choirs",36,-22.0,27319),
       "p_meeting":("Sentinel Point","Ventilation, writing at the table and settling timber",41,-25.0,48209),
       "p_bay":("Bellwether Bay","Water against both sides of the boat, hull flex and a distant mooring",44,-21.0,71903)}
TAKE={"p_veyr":"p_veyr.in.02","p_meeting":"p_meeting.in.01","p_bay":"p_bay.in.01"}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def db(value):return 20*math.log10(max(1e-12,value))

def band(noise,low,high):
    return signal.sosfilt(signal.butter(3,[low,high],btype="bandpass",fs=RATE,output="sos"),noise)

def colored(rng,size,lo,hi):
    track=band(rng.standard_normal(size),lo,hi)
    return track/max(np.std(track),1e-7)

def drift(rng,t,knot,low,high):
    tick=np.arange(-knot,t[-1]+knot*2,knot)
    return PchipInterpolator(tick,rng.uniform(low,high,len(tick)))(t)

def pan(p):
    return np.array((math.cos((p+1)*math.pi/4),math.sin((p+1)*math.pi/4)))

def place(mix,a,time,p,gain=1):
    start=round(time*RATE)
    end=min(len(mix),start+len(a))
    if end>start:mix[start:end]+=a[:end-start,None]*pan(p)*gain

def diffuse(mono,taps):
    result=np.zeros((len(mono),2))
    for seconds,p,amp in taps:place(result,mono,seconds,p,amp)
    return result

def impulse_voice(t,f,rng,decay=24):
    phase=rng.uniform(0,2*math.pi,3)
    return sum(np.sin(2*math.pi*freq*t+p)*np.exp(-d*t)*level for freq,d,level,p in zip(
      (f,f*1.62,f*2.41),(decay,decay*1.45,decay*2),(.62,.27,.11),phase))

def tower(rng,t,pitches):
    result=np.zeros(len(t)); length=t[-1]
    for j,base in enumerate(pitches):
        breath=drift(rng,t,2.9,.21,.96)
        phase_noise=drift(rng,t,.9,-.007,.007)
        slow=np.sin(2*math.pi*(.045+j*.027)*t+rng.uniform(0,6.28))
        f=base*(1+phase_noise+.0014*np.sin(2*math.pi*(3.5+j*.47)*t))
        ph=np.cumsum(f)/RATE*2*math.pi+rng.uniform(0,6.28)
        # The distant vowel shifts from oo to ah. Slightly different formants
        # and pitches per singer avoid a single, stationary electronic note.
        v1=385+81*slow; v2=1210+180*np.sin(.19*t+j)
        voice=np.zeros(len(t))
        for h in range(1,12):
            hz=base*h
            mag=(.27/(h**1.2)+.31*np.exp(-.5*((hz-v1)/120)**2)
                 +.14*np.exp(-.5*((hz-v2)/190)**2))/(h**.42)
            voice+=mag*np.sin(ph*h+rng.uniform(0,6.28))
        result+=voice*breath*(.83+.17*np.sin(2*math.pi*t/(length*.61)+j))
    return result

def veyr(rng,t):
    n=len(t)
    common=colored(rng,n,62,315); high=colored(rng,n,315,1950)
    tide=drift(rng,t,2.65,.24,.91)
    wind=common*.15*tide+high*.032*(.3+tide**1.9)
    m=diffuse(wind,[(0,-.10,.89),(.031,.66,.22),(.066,-.81,.15)])
    for p in (-.88,.85):
        air=colored(rng,n,145,1050)*drift(rng,t,1.8,.03,.14)
        silk=colored(rng,n,1150,3800)*drift(rng,t,2.0,.002,.012)
        place(m,air+silk,0,p)
    for pitches,taps in [((144.8,217.4,289.5),[(0,-.68,.10),(.081,.25,.043),(.192,.82,.026)]),
                         ((180.7,216.9,324.8),[(0,.7,.049),(.109,-.45,.026),(.235,-.87,.017)])]:
        m+=diffuse(tower(rng,t,pitches),taps)
    return m

def wood(rng,duration,grain,frequency):
    t=np.arange(round(duration*RATE))/RATE
    # Friction excites the wood in small, irregular slips rather than one sine sweep.
    stream=np.zeros(len(t)); now=.018
    while now<duration-.02:
        i=int(now*RATE); stream[i]=rng.uniform(.32,.95)
        now+=rng.uniform(.005,.016)*(1+.85*(now/duration)**2)
    resonant=np.zeros(len(t))
    for f,w in ((frequency,.85),(frequency*1.54,.5),(frequency*3.08,.22)):
        radius=np.exp(-math.pi*grain/RATE)
        resonant+=w*signal.lfilter([1],[1,-2*radius*np.cos(2*math.pi*f/RATE),radius**2],stream)
    resonant/=max(np.max(abs(resonant)),1e-7)
    return resonant*np.sin(math.pi*t/duration)**1.45

def pen(rng):
    # Four strokes and a pen lift; each changes speed and nib pressure.
    length=rng.uniform(.51,.85); t=np.arange(round(RATE*length))/RATE
    tt=t/length
    pressure=sum(rng.uniform(.45,.9)*np.exp(-.5*((tt-p)/w)**2) for p,w in [
        (.10,.045),(.27,.084),(.49,.050),(.68,.070),(.83,.033)])
    grit=colored(rng,len(t),1050,4700)
    nip=colored(rng,len(t),420,1400)
    return (.61*grit+.28*nip)*pressure*np.sin(math.pi*tt)**.8

def meeting(rng,t):
    n=len(t); motor=np.cumsum(59.81*(1+drift(rng,t,4.2,-.001,.001)))*2*math.pi/RATE
    tone=.015*np.sin(motor)+.008*np.sin(2*motor+.15)+.0018*np.sin(4*motor+1.2)
    supply=colored(rng,n,64,310)*.067*drift(rng,t,2.9,.73,1.1)
    m=diffuse(tone+supply,[(0,-.22,.89),(.016,.64,.32)])
    for p in (-.76,.76):
        place(m,colored(rng,n,190,1150)*.026+colored(rng,n,850,3300)*.005,0,p)
    for when,p in ((4.25,.34),(17.82,-.19),(18.98,-.19),(32.92,.22)):
        a=pen(rng);place(m,a,when,p,.075);place(m,a,when+.023,-p,.009)
    for when,p,duration,freq in [(10.9,-.67,.47,190),(28.42,.52,.34,268),(37.77,-.26,.26,315)]:
        a=wood(rng,duration,38,freq);place(m,a,when,p,.39);place(m,a,when+.038,-p,.053)
        strike=np.arange(round(.14*RATE))/RATE
        place(m,impulse_voice(strike,freq*.66,rng,29),when+duration*.76,p,.088)
    return m

def lap(rng,duration):
    t=np.arange(round(RATE*duration))/RATE; rel=t/duration
    crest=.13+rng.uniform(0,.1)
    attack=1-np.exp(-np.maximum(rel-.015,0)/.048)
    e=attack*np.exp(-np.maximum(rel-crest,0)/.21)
    current=colored(rng,len(t),95,660)*(.37*e)
    wash=colored(rng,len(t),470,2600)*(.16*e**1.7)
    retreat=colored(rng,len(t),270,1480)*(.09*np.exp(-.5*((rel-.59)/.14)**2))
    water=current+wash+retreat
    # Individual bubbles ring briefly at slightly different depths as a wave retreats.
    for _ in range(rng.integers(4,10)):
        start=rng.uniform(crest*.65,min(.87,crest+.47))*duration
        delta=t-start;tt=np.maximum(delta,0)
        f=rng.uniform(310,1100); decay=rng.uniform(28,88)
        wave=np.sin(2*math.pi*(f*tt+f*rng.uniform(.8,3)*tt*tt))
        water+=rng.uniform(.035,.12)*wave*(1-np.exp(-tt/.0012))*np.exp(-tt*decay)*(delta>0)
    return water*np.minimum(1,t/.014)*np.minimum(1,np.maximum(0,duration-t)/.025)

def bay(rng,t):
    n=len(t);under=colored(rng,n,55,350)*drift(rng,t,3,.036,.074)
    m=diffuse(under,[(0,-.05,.86),(.041,.7,.27),(.071,-.71,.21)])
    for p in (-.83,.82):
        place(m,colored(rng,n,270,1450)*.023,0,p)
        at=rng.uniform(.1,1.4)
        while at<t[-1]-.6:
            a=lap(rng,rng.uniform(.78,1.68));gain=rng.uniform(.19,.47)
            place(m,a,at,p+rng.uniform(-.07,.07),gain)
            place(m,a,at+rng.uniform(.034,.064),-p*.6,gain*.16)
            at+=rng.uniform(1.44,3.21)
    for at,p,f in [(6.2,-.16,164),(21.1,.48,224),(38.58,-.39,193)]:
        a=wood(rng,rng.uniform(.34,.73),42,f);place(m,a,at,p,.32)
    for at in (13.3,14.61,31.12):
        ts=np.arange(round(.74*RATE))/RATE
        ring=sum(g*np.sin(2*math.pi*f*ts+rng.uniform(0,6.28))*np.exp(-ts*d)
                 for f,g,d in ((294,.59,7),(535,.24,10.7),(912,.14,16),(1577,.05,23)))
        ring*=1-np.exp(-ts/.002)
        place(m,ring,at,.63,.057);place(m,ring,at+.1,-.2,.012)
    return m

def loudness(path):
    proc=subprocess.run(["ffmpeg","-nostats","-hide_banner","-i",str(path),"-af","ebur128=peak=true",
                         "-f","null","-"],check=True,capture_output=True,text=True)
    return (float(re.findall(r"I:\s*([-\d.]+) LUFS",proc.stderr)[-1]),
            float(re.findall(r"Peak:\s*([-\d.]+) dBFS",proc.stderr)[-1]))

def write_scene(key,recipe,cache,masters,runtime):
    place_name,description,seconds,target,seed=recipe
    rng=np.random.default_rng(seed);n=seconds*RATE
    t=np.arange(n+OVERLAP*RATE)/RATE
    audio={"p_veyr":veyr,"p_meeting":meeting,"p_bay":bay}[key](rng,t)
    # The left side of the cut continues into the original tail at the beginning
    # of the loop. Crossfade that tail back into the original head over two seconds.
    L=RATE*OVERLAP; phase=np.arange(L)/(L-1)*math.pi/2
    audio[:L]=audio[n:n+L]*np.cos(phase[:,None])**2+audio[:L]*np.sin(phase[:,None])**2
    main=audio[:n];main-=np.mean(main,axis=0)
    probe=cache/(key+".wav");sf.write(probe,main,RATE,subtype="FLOAT")
    gain=10**((target-loudness(probe)[0])/20)
    main*=gain
    if abs(main).max()>.85:raise ValueError(f"Insufficient mastering headroom {key}: {abs(main).max():.2f}")
    master=masters/(key+".wav");sf.write(master,main,RATE,subtype="PCM_24")
    output=runtime/(key+".ogg")
    with sf.SoundFile(output,"w",RATE,2,format="OGG",subtype="VORBIS",compression_level=.48) as stream:
        stream.title=place_name
        for start in range(0,n,4096):
            stream.write(main[start:start+4096])
    return inspect_scene(key,recipe,master,output)

def inspect_scene(key,recipe,master,output):
    place_name,description,seconds,target,seed=recipe
    n=seconds*RATE
    decoded,rate=sf.read(output,dtype="float32")
    if rate!=RATE or decoded.shape!=(n,2):raise ValueError((rate,decoded.shape))
    jumps=abs(np.diff(decoded,axis=0))
    seam=abs(decoded[-1]-decoded[0])
    if np.any(seam>np.quantile(jumps,.995,axis=0)):raise ValueError(f"Discontinuous decoded loop {key}")
    li,pk=loudness(output)
    if abs(li-target)>.5:raise ValueError("Decoded level changed: "+key)
    take=ROOT/"game/assets/audio/voices"/(TAKE[key]+".wav"); speech,_=loudness(take)
    return {"scene":place_name,"audible_elements":description,"seed":seed,"sample_rate":rate,
        "channels":2,"frames":n,"loop_seconds":seconds,"loop_start":0,"loop_end":n,
        "master_pcm_bits":24,"master_sha256":digest(master),"runtime_file":f"res://assets/audio/ambience-prologue/{key}.ogg",
        "runtime_sha256":digest(output),"runtime_bytes":output.stat().st_size,"integrated_lufs":li,"true_peak_dbtp":pk,
        "channel_correlation":round(float(np.corrcoef(decoded.T)[0,1]),3),"wrap_delta_dBFS":
         [round(db(x),1) for x in seam],"runtime_gain_db":-12,"dialogue_test":TAKE[key],
        "dialogue_lufs":speech,"under_dialogue_db":round(speech-(li-12),1)}

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--masters",type=Path,default=MASTERS)
    parser.add_argument("--runtime",type=Path,default=RUNTIME)
    parser.add_argument("--verify-existing",action="store_true")
    args=parser.parse_args()
    args.masters.mkdir(exist_ok=True,parents=True);args.runtime.mkdir(exist_ok=True,parents=True)
    result={}
    with tempfile.TemporaryDirectory() as tmp:
        for key,recipe in ROLES.items():
            if args.verify_existing:
                result[key]=inspect_scene(key,recipe,args.masters/(key+".wav"),args.runtime/(key+".ogg"))
            else:
                result[key]=write_scene(key,recipe,Path(tmp),args.masters,args.runtime)
            print(key,result[key],flush=True)
    (args.masters/"ambience.json").write_text(json.dumps(result,indent=2)+"\n")
if __name__=="__main__":main()
