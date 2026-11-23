#!/usr/bin/env python3
"""Offline transcript checks for candidate voices. Listening review is still required."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NORMALIZATION_VERSION='whisper_english_orthography_v2'

def raw_words(text):
    text=text.lower().replace('’',"'")
    for call in ['kay seven bee ell double you','k seven b l w','k7blw']:
        text=text.replace(call,'k7blw')
    return re.findall(r"[\w]+(?:'[\w]+)?",text)

def words(text):
    # Standard ASR normalization handles numeric formatting and contractions.
    # Preserve the raw transcript and raw error count in every report.
    from transformers.models.whisper.english_normalizer import EnglishTextNormalizer
    text=text.lower().replace('’',"'")
    text=re.sub(r'\bk\s*7\s*b\s*l\s*w\b','k7blw',text)
    for call in ['kay seven bee ell double you','k seven b l w']:
        text=text.replace(call,'k7blw')
    normalized=EnglishTextNormalizer({})(text)
    # Spoken equivalents. The raw recognition remains available for review.
    # Steve's copy Stephen and the formal name Steven use the same pronunciation.
    # British and American spellings of one spoken word are the same word.
    for pattern,replacement in [(r'\bstephen\b','steven'),(r'\banytime\b','any time'),
                                (r'\beveryone\b','every one'),(r'\bre syncs\b','resyncs'),
                                (r'\bcancell(ing|ed)\b',r'cancel\1')]:
        normalized=re.sub(pattern,replacement,normalized)
    return normalized.split()

def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        following=[i]
        for j,y in enumerate(b,1):
            following.append(min(row[j]+1,following[-1]+1,row[j-1]+int(x!=y)))
        row=following
    return row[-1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wav',type=Path,nargs='+')
    p.add_argument('--model',type=Path,help='Existing local MLX Whisper model directory')
    p.add_argument('--story-vocabulary',action='store_true',help='Supply character/place spellings, never the expected line')
    p.add_argument('--force-transcribe',action='store_true',help='Re-run ASR and preserve the previous report')
    args=p.parse_args()
    if args.model is None:
        args.model=ROOT/'.tools/models/whisper-qa'
    if not any((args.model/name).exists() for name in ['weights.npz','weights.safetensors','model.safetensors']):
        p.error('Provide a complete local Whisper model. This checker never downloads weights.')
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from mlx_audio.stt import load
    import numpy as np
    import soundfile as sf
    engine=None
    for path in args.wav:
        metadata=json.loads(path.with_suffix('.json').read_text())
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=metadata['sha256']:
            raise SystemExit('Candidate hash mismatch: '+str(path))
        audio,rate=sf.read(str(path),dtype='float32')
        if audio.ndim!=1 or not np.isfinite(audio).all():
            raise SystemExit('Expected finite mono candidate audio.')
        expected=metadata.get('spoken_text',metadata['text'])
        output=ROOT/'tmp/qa/voices'/(path.stem+'.json')
        cached=json.loads(output.read_text()) if output.exists() else {}
        vocabulary=''
        if args.story_vocabulary:
            vocabulary=('Night Nine. Steve Mercer, Stephen, Nora Reyes, Iris, Helen, Frank, Agnes Penhallow, '
                'June Calder, Evelyn Shaw, Mateo, Rafa, La Marea, Rook, Saren, Wick, Veyr, Tirel, Bellwether, K7BLW. '
                'Sound engineering terms: all-call, cue number, re-sync.')
        if not args.force_transcribe and cached.get('sha256')==sha and cached.get('expected')==expected:
            recognized=cached['recognized']
            segments=cached.get('segments',[])
        else:
            if engine is None:engine=load(str(args.model))
            result=engine.generate(str(path),language='en',
                temperature=0,condition_on_previous_text=False,word_timestamps=True,
                initial_prompt=vocabulary or None)
            recognized=result.text
            segments=result.segments or []
        reference=words(expected)
        hypothesis=words(recognized)
        edits=distance(reference,hypothesis)
        ratio=edits/max(1,len(reference))
        raw_reference=raw_words(expected)
        raw_edits=distance(raw_reference,raw_words(recognized))
        report={'candidate':str(path),'sha256':sha,'expected':expected,'recognized':recognized,
            'word_error_rate':ratio,'word_edits':edits,'seconds':len(audio)/rate,
            'normalization_version':NORMALIZATION_VERSION,
            'vocabulary_prompt':vocabulary or cached.get('vocabulary_prompt',''),
            'normalized_expected':' '.join(reference),'normalized_recognized':' '.join(hypothesis),
            'raw_word_edits':raw_edits,'raw_word_error_rate':raw_edits/max(1,len(raw_reference)),
            'peak':float(np.max(np.abs(audio))),'asr_model':str(args.model),
            'transcript_flag':'review_mismatch' if ratio>0.15 else 'close_match',
            'listening_review_required':True,'segments':segments}
        output.parent.mkdir(parents=True,exist_ok=True)
        if args.force_transcribe and output.exists():
            prior=output.with_suffix('.previous.json')
            if not prior.exists():prior.write_text(output.read_text())
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({key:report[key] for key in ['candidate','recognized','word_error_rate','transcript_flag']}),flush=True)

if __name__=='__main__': main()
