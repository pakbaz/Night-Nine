#!/usr/bin/env python3
"""Original, deterministic non-speech sound cues and seamless ambient beds.

These are synthesized game sound effects, not character recordings or licensed music.
"""
import array
import hashlib
import json
import math
import random
import wave
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'game/assets/audio'
RATE=24000

def write(name, values, folder='effects'):
    path=OUT/folder/(name+'.wav')
    path.parent.mkdir(parents=True,exist_ok=True)
    samples=array.array('h',(int(max(-0.95,min(0.95,v))*32767) for v in values))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(samples.tobytes())
    return {'file':'res://assets/audio/'+folder+'/'+path.name,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'seconds':len(samples)/RATE,
            'provenance':'Original deterministic synthesis in tools/build-soundscape.py'}

def tone(freq, duration, volume=.25):
    count=int(duration*RATE)
    return [volume*math.sin(2*math.pi*freq*i/RATE)*min(1,i/(RATE*.02),(count-i)/(RATE*.04)) for i in range(count)]

def chord(frequencies, duration, volume=.2):
    count=int(duration*RATE)
    return [volume*sum(math.sin(2*math.pi*f*i/RATE) for f in frequencies)/len(frequencies)
            * min(1,i/(RATE*.02),(count-i)/(RATE*.04)) for i in range(count)]

def silence(seconds):
    return [0.0]*int(seconds*RATE)

def aquarium_corridors():
    rng = random.Random(917)
    cycle = silence(2)
    bell = tone(732, .18, .23)
    cycle[int(.19*RATE):int(.19*RATE)+len(bell)] = bell
    # A short, two-part intercom cough after the bell. Repeat the actual captured cycle.
    low = 0.0
    for i in range(int(.38*RATE)):
        t = i/RATE
        low = .81*low + .19*rng.uniform(-1,1)
        envelope = math.exp(-((t-.075)/.042)**2) + .75*math.exp(-((t-.24)/.066)**2)
        cycle[int(.69*RATE)+i] = .56*low*envelope
    footsteps = silence(6)
    for start, weight in [(.24,1),(.80,.8),(1.33,1.1),(2.70,.74),(3.11,1.0),(4.72,.86),(5.20,1.08)]:
        for i in range(int(.23*RATE)):
            t = i/RATE
            attack = min(t/.012,1.0)*math.exp(-t*20)
            footsteps[round(start*RATE)+i] += weight*attack*(.44*math.sin(2*math.pi*74*t)+.065*rng.uniform(-1,1))
    return {'aquarium_pa':cycle*3, 'aquarium_steps':footsteps}

def evidence_sounds():
    sounds = aquarium_corridors()
    # The two national reports use this same test take, including its damaged cadence.
    sounds['meridian_pulse'] = (silence(.25) + tone(300,.21) + silence(.14) + tone(365,.21) +
                               silence(.14) + tone(420,.07) + silence(.49) + tone(520,.56) +
                               silence(.19) + tone(368,.18) + silence(.28))
    return {name:write(name, samples) for name,samples in sounds.items()}

def ambient(style, seed):
    rng=random.Random(seed)
    length=12*RATE
    low=0
    noise=[]
    for i in range(length):
        low=.985*low+.015*rng.uniform(-1,1)
        t=i/RATE
        sea=style in ['pier','boat','beach','finale','balcony','street']
        alien=style in ['ship','gallery','choir','veyr']
        amplitude=.55+.25*math.sin(2*math.pi*t/6) if sea else .23
        base=low*amplitude
        if alien:
            base+=.026*math.sin(2*math.pi*110*t)+.018*math.sin(2*math.pi*165*t)+.01*math.sin(2*math.pi*220*t)
        elif style in ['station','radio_shack','safehouse','lab','aquarium']:
            base+=.008*math.sin(2*math.pi*60*t)+.004*math.sin(2*math.pi*120*t)
        noise.append(base)
    # Crossfade the final quarter second into the beginning and shorten the loop.
    blend=RATE//4
    for i in range(blend):
        a=i/blend
        noise[i]=noise[length-blend+i]*(1-a)+noise[i]*a
    return noise[:-blend]

def prepare_delegate_reaction():
    source = ROOT / "assets/audio/delegate-reaction/delegates_laugh.wav"
    receipt = json.loads(source.with_suffix(".json").read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != receipt["sha256"]:
        raise ValueError("Delegate reaction master differs from the production receipt")
    dest = OUT / "effects/delegates_laugh.wav"
    with wave.open(str(source), "rb") as original, wave.open(str(dest), "wb") as wav:
        # In Godot, start the reaction when the current VO ends. The original master
        # included a lead-in timed specifically to an earlier spoken take.
        original.setpos(round(original.getframerate() * receipt["reaction_onset_seconds"]))
        pcm = original.readframes(original.getnframes())
        wav.setparams(original.getparams())
        wav.writeframes(pcm)
    with wave.open(str(dest), "rb") as result:
        seconds = result.getnframes() / result.getframerate()
    return {"file": "res://assets/audio/effects/delegates_laugh.wav", "seconds": seconds,
            "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
            "provenance": "assets/audio/delegate-reaction/delegates_laugh.json"}


def main():
    manifest={}
    styles=sorted({s['style'] for s in json.loads((ROOT/'game/content/campaign.json').read_text())['scenes']})
    for i,style in enumerate(styles):
        manifest[style]=write(style,ambient(style,100+i),'ambience')
    manifest['delegates_laugh'] = prepare_delegate_reaction()
    manifest['nora_whistle']=write('nora_whistle',tone(739.989,.32)+silence(.16)+tone(880,.5))
    manifest['nora_whistle_flat']=write('nora_whistle_flat',tone(739.989,.32)+silence(.16)+tone(698.456,.5))
    rng=random.Random(210)
    breath=[.08*rng.uniform(-1,1)*math.sin(math.pi*i/(RATE*.8)) for i in range(int(RATE*.8))]
    manifest['steve_whistle']=write('steve_whistle',breath+tone(739.989,.24,.12)+silence(.19)+tone(880,.37,.13))
    winch=[]
    for i in range(RATE*3):
        t=i/RATE
        winch.append(.1*math.sin(2*math.pi*46*t)+.025*math.sin(2*math.pi*92*t)+.018*math.sin(2*math.pi*7*t))
    manifest['harbor_winch']=write('harbor_winch',winch)
    ident=[]
    for frequency in (220,277.183,329.628,440):
        ident+=tone(frequency,.55,.15)+silence(.08)
    ident+=chord((220,277.183,329.628),1.2,.13)
    ident=(ident+silence(12))[:RATE*12]
    manifest['kbwr_ident']=write('kbwr_ident',ident)
    pattern={'K':'-.-','7':'--...','B':'-...','L':'.-..','W':'.--'}
    morse=[]
    unit=.09
    for letter in 'K7BLW':
        for symbol in pattern[letter]:
            morse+=tone(680,unit*(3 if symbol=='-' else 1),.21)+silence(unit)
        morse+=silence(2*unit)
    manifest['k7blw']=write('k7blw',morse)
    motif=[]
    # An original six-note phrase. Reuse it for the early hum and Helen's wake-up cue.
    for frequency,duration in [(220,.65),(261.626,.65),(293.665,1.0),(261.626,.65),(196,.65),(220,1.3)]:
        motif+=tone(frequency,duration,.13)+silence(.08)
    manifest['lullaby']=write('lullaby',motif)
    manifest['veyr_wind']=write('veyr_wind',ambient('veyr',900),'effects')
    manifest['new_wind']=write('new_wind',ambient('veyr',901),'effects')
    manifest['wick']=write('wick',tone(220,.8)+tone(330,1.1)+silence(.5)+tone(165,2.0))
    manifest['wick_high_ending']=write('wick_high_ending',tone(220,.8)+tone(330,1.1)+silence(.5)+tone(440,2.0))
    hold=[]
    for frequency in (261.626,329.628,392,329.628,293.665,349.228,440,392):
        hold+=tone(frequency,.34,.1)+silence(.06)
    manifest['halcyon_hold_seattle']=write('halcyon_hold_seattle',tone(440,.12,.08)+silence(.25)+hold)
    manifest['halcyon_hold_denver']=write('halcyon_hold_denver',tone(523.251,.12,.08)+silence(.55)+hold)
    manifest.update(evidence_sounds())
    # Generated recordings are built by their own tools; keep their entries.
    # tools/build-bay-hum.py: the ninth-night choir. tools/build-story-effects.py: story moments.
    previous=OUT/'soundscape-manifest.json'
    kept={'assets/audio/bay-hum/bay-hum.json','assets/audio/story-effects/story-effects.json'}
    if previous.exists():
        manifest.update({name:entry for name,entry in json.loads(previous.read_text()).items()
                         if entry.get('provenance') in kept})
    (OUT/'soundscape-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'original_cues':len(manifest),'ambient_styles':len(styles)}))

if __name__=='__main__':
    main()
