import subprocess, sys, array, math, json, os
SR=11025; HOP=256
def onset_env(path):
    raw=subprocess.run(['ffmpeg','-v','error','-i',path,'-ac','1','-ar',str(SR),'-f','s16le','-'],capture_output=True).stdout
    a=array.array('h'); a.frombytes(raw)
    n=len(a)//HOP
    # 3-band-ish: full energy log + high-passed (first difference) energy log
    e=[];h=[]
    prev=0
    for i in range(n):
        seg=a[i*HOP:(i+1)*HOP]
        s=0.0; d=0.0; p=seg[0]
        for x in seg:
            s+=x*x; d+=(x-p)*(x-p); p=x
        e.append(math.log1p(s/HOP)); h.append(math.log1p(d/HOP))
    env=[max(0,h[i]-h[i-1])+0.5*max(0,e[i]-e[i-1]) for i in range(1,n)]
    env=[0]+env
    return env
def tempo(env, lo=60, hi=170):
    fps=SR/HOP
    m=sum(env)/len(env)
    x=[v-m for v in env]
    best=[]
    for bpm10 in range(lo*10,hi*10+1,5):
        bpm=bpm10/10
        lag=fps*60/bpm
        L=int(lag); fr=lag-L
        c=0.0
        for i in range(len(x)-L-1):
            c+=x[i]*((1-fr)*x[i+L]+fr*x[i+L+1])
        best.append((c,bpm))
    best.sort(reverse=True)
    return best[:5]
def phase(env,bpm):
    fps=SR/HOP; period=fps*60/bpm
    best=(0,0)
    for k in range(int(period)):
        s=0; t=k
        while t<len(env):
            s+=env[int(t)]; t+=period
        if s>best[0]: best=(s,k)
    return best[1]/fps
if __name__=='__main__':
    out={}
    for p in sys.argv[1:]:
        env=onset_env(p)
        tb=tempo(env)
        bpm=tb[0][1]
        ph=phase(env,bpm)
        # clarity: ratio of best to median correlation
        out[os.path.basename(p)]={'bpm':bpm,'first_beat':round(ph,3),'candidates':[(round(c,1),b) for c,b in tb]}
        print(os.path.basename(p), json.dumps(out[os.path.basename(p)]), flush=True)
