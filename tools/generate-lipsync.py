#!/usr/bin/env python3
"""Generate local transcript-guided mouth cues, preserving the recorded audio."""
import argparse,concurrent.futures,hashlib,json,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BINARY=ROOT/'.tools/rhubarb-1.14.0/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb'
SYMBOLS=set('ABCDEFGHX')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def validate(raw,duration):
    cues=raw['mouthCues'];previous=0.0
    if not cues:raise ValueError('No mouth cues were generated.')
    for cue in cues:
        start,end=float(cue['start']),float(cue['end'])
        if cue['value'] not in SYMBOLS or start<0 or end<=start or abs(start-previous)>.0001:
            raise ValueError('Invalid or discontinuous cue: '+str(cue))
        previous=end
    if abs(previous-duration)>.011 or abs(float(raw['metadata']['duration'])-duration)>.011:
        raise ValueError('Cue duration does not match the recorded audio.')
    if not any(cue['value']!='X' for cue in cues):raise ValueError('No speech motion was detected.')
    return cues

def generate_cues(line, take, folder, binary_hash, version):
    audio=ROOT/'game'/take['file'].removeprefix('res://')
    folder.mkdir(parents=True,exist_ok=True)
    audio_hash=sha(audio)
    if audio_hash!=take['sha256']:raise ValueError('Recording hash changed: '+line)
    text=take.get('spoken_text',take['text']);text_hash=hashlib.sha256(text.encode()).hexdigest()
    receipt_path=folder/(line+'.json');raw_path=folder/(line+'.raw.json')
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text())
        if (receipt['audio_sha256'],receipt['transcript_sha256'],receipt['generator_sha256'])!=(audio_hash,text_hash,binary_hash):
            raise ValueError('Preserve the prior cues and use a new revision for '+line)
        if sha(raw_path)!=receipt['raw_sha256']:
            raise ValueError('Cached generator output changed: '+line)
        cues=validate(json.loads(raw_path.read_text()),take['seconds'])
        if cues!=receipt['cues'] or receipt['transcript']!=text:
            raise ValueError('Cached timing or transcript changed: '+line)
        return receipt
    dialog=folder/(line+'.txt');dialog.write_text(text)
    pending=folder/(line+'.raw.partial.json')
    command=[str(BINARY),'-r','pocketSphinx','-f','json','-d',str(dialog),'--threads','1',
             '--extendedShapes','GHX','--machineReadable','-q','-o',str(pending),str(audio)]
    started=time.monotonic()
    result=subprocess.run(command,text=True,capture_output=True,timeout=180)
    (folder/(line+'.log')).write_text(result.stderr)
    if result.returncode!=0:raise RuntimeError('Rhubarb failed for '+line+': '+result.stderr[-500:])
    raw=json.loads(pending.read_text());cues=validate(raw,take['seconds']);pending.replace(raw_path)
    receipt={'id':line,'speaker':take['speaker'],'audio':take['file'],'audio_sha256':audio_hash,
             'transcript':text,'transcript_sha256':text_hash,'generator':version,'generator_sha256':binary_hash,
             'seconds':take['seconds'],'generation_seconds':round(time.monotonic()-started,3),
             'cues':cues,'raw_sha256':sha(raw_path),'visual_timing_reviewed':False,
             'cloud_credits':0,'uploads':False}
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--line',action='append',default=[])
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--revision',help='Override the active timing revision for each recording')
    a=p.parse_args()
    if a.revision and not a.revision.replace('-','').isalnum():raise SystemExit('Use a simple revision name.')
    takes=json.loads((ROOT/'game/content/voice-manifest.json').read_text())['takes']
    selected=a.line or list(takes)
    if any(line not in takes for line in selected):raise SystemExit('Unknown dialogue ID.')
    binary_hash=sha(BINARY)
    version=subprocess.check_output([str(BINARY),'--version'],text=True).strip()
    def cue_folder(take):
        revision=a.revision or take.get('lip_sync_revision','v1')
        if not revision.replace('-','').isalnum():raise ValueError('Invalid cue revision.')
        return ROOT/'assets/audio'/('lipsync-'+revision)
    def run(line):
        take=takes[line]
        return generate_cues(line,take,cue_folder(take),binary_hash,version)
    completed=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.workers,4))) as pool:
        jobs={pool.submit(run,line):line for line in selected}
        for future in concurrent.futures.as_completed(jobs):
            result=future.result();completed+=1
            if completed%20==0 or completed==len(selected):
                print(json.dumps({'completed':completed,'requested':len(selected),'last':result['id']}),flush=True)
    receipts=[]
    for line,take in takes.items():
        folder=cue_folder(take)
        path=folder/(line+'.json')
        if not path.exists():continue
        receipt=json.loads(path.read_text())
        audio=ROOT/'game'/take['file'].removeprefix('res://')
        text=take.get('spoken_text',take['text'])
        text_hash=hashlib.sha256(text.encode()).hexdigest()
        raw_path=folder/(line+'.raw.json')
        if (receipt['audio_sha256']!=take['sha256'] or sha(audio)!=take['sha256']
                or receipt['generator_sha256']!=binary_hash or receipt['transcript_sha256']!=text_hash
                or receipt['transcript']!=text or sha(raw_path)!=receipt['raw_sha256']):
            raise ValueError('Stale receipt for '+line)
        if validate(json.loads(raw_path.read_text()),take['seconds'])!=receipt['cues']:
            raise ValueError('Cached mouth cues changed: '+line)
        validate({'mouthCues':receipt['cues'],'metadata':{'duration':receipt['seconds']}},take['seconds'])
        receipts.append(receipt)
    if len(receipts)!=len(takes):
        print(json.dumps({'cached_takes':len(receipts),'total_takes':len(takes),'runtime_manifest_written':False}))
        return
    runtime={'schema':1,'generator':version,'source':'https://github.com/DanielSWolf/rhubarb-lip-sync',
             'takes':{r['id']:{'audio_sha256':r['audio_sha256'],'seconds':r['seconds'],
                             'cues':r['cues'],'visual_timing_reviewed':False} for r in receipts}}
    manifest=ROOT/'game/content/lipsync-manifest.json';manifest.write_text(json.dumps(runtime,separators=(',',':'))+'\n')
    report={'takes':len(receipts),'cue_count':sum(len(r['cues']) for r in receipts),
            'source_audio_hashes_verified':len(receipts),'transcripts_provided':len(receipts),
            'duration_and_continuity_checks_passed':len(receipts),'generator':version,'generator_sha256':binary_hash,
            'manifest_sha256':sha(manifest),'visual_timing_reviews_completed':0,'production_facial_performance_complete':False,
            'cloud_credits':0,'uploads':False,'receipt_folders':sorted({cue_folder(take).relative_to(ROOT).as_posix() for take in takes.values()})}
    (ROOT/'docs/verification/lipsync-timing.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
