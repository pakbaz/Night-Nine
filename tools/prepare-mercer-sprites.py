"""Build seated Mercer eye and mouth patches from their approved cutout pixels."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location("sprite_patches",HERE/"prepare-archivist-sprite.py")
art=importlib.util.module_from_spec(spec)
spec.loader.exec_module(art)

FACES={
 "helen":{
  "eyes":(500,174,174,68),"mouth":(503,277,133,63),"size":(1086,1448),
  "upper":[[(515,194),(520,190),(526,187.8),(533,186.4),(540,186.8),(547,189),(555,193.5),(561,199),(564.5,203.1)],
           [(615.4,215.5),(619.5,211.9),(626,208.6),(632.5,206.8),(638,207.3),(644,208.8),(651,213.4),(656.4,222)]],
  "lower":[[(515,194),(520,194.6),(526,197.5),(534,199.8),(542,201),(550,201.3),(556,201),(561,202),(564.5,203.1)],
           [(615.4,215.5),(619,215.6),(625,217.6),(632,220.3),(639,222.2),(646,223.7),(652,224),(656.4,222)]],
  "seam":[(525,294.6),(534.5,297.2),(545,299),(556.5,300.5),(568,302),(579.5,304.8),(591,307),(602,309.3),(613.4,314.1)],
  "centers":[[535,193],[633,214]],"dental":(548,197),"opening":9.8,
 },
 "frank":{
  "eyes":(582,193,197,70),"mouth":(626,299,163,79),"size":(1312,1199),
  "upper":[[(598,244),(603,238.5),(609,233.5),(616,229.5),(622,226.3),(628,224.9),(633,225.3),(638,228),(645.5,233)],
           [(712.8,223.3),(717.5,217.3),(723,212.1),(729.5,208),(736,205.6),(743,205.8),(750,207.4),(756,210.6),(763,215.5)]],
  "lower":[[(598,244),(603,239.8),(609,239),(616,238.8),(623,238.2),(629,236.8),(635,234.8),(640,233.7),(645.5,233)],
           [(712.8,223.3),(718.5,220),(725,218.5),(731,218.1),(738,217.6),(744.5,216.6),(750,214.3),(755.5,212.2),(763,215.5)]],
  "seam":[(646.5,350.8),(658,348.8),(670,347.1),(681.5,344.4),(692,341.8),(704,339.5),(715.5,338),(727,334.5),(739,331.1),(750.4,329.4),(758.7,326.5),(766,323.9)],
  "centers":[[626,230],[740,211]],"dental":(613,236),"opening":12.0,
 },
}
CUES={"X":None,"A":None,"B":"mouth_parted","C":"mouth_wide","D":"mouth_open",
      "E":"mouth_round","F":"mouth_round","G":"mouth_parted","H":"mouth_parted"}

def prepare(name,review):
    settings=FACES[name];folder=ROOT/"assets/characters"/name/"sprites"
    source=folder/(name+".png")
    neutral=Image.open(source).convert("RGBA");width,height=neutral.size
    if neutral.size!=settings["size"]:raise ValueError("Unexpected authored dimensions: "+str(neutral.size))
    rgb=np.asarray(neutral.convert("RGB"),dtype=np.float32)
    eyes,mouth=settings["eyes"],settings["mouth"]
    px,py=settings["dental"]
    dental=np.median(rgb[py-1:py+2,px-1:px+2],axis=(0,1))
    patches={}
    for key,weight in (("blink_half",.52),("blink_closed",1.0)):
        patches[key]=(eyes,art.blink(rgb,weight,settings["upper"],settings["lower"],eyes,human_lids=True))
    for key,opening,rounding,spread in (("mouth_parted",.38,0,0),("mouth_open",1,0,.008),
                                        ("mouth_round",1.15,1.30,-.095),("mouth_wide",.55,0,.044)):
        piece=art.lips(rgb,settings["opening"]*opening,rounding,spread,settings["seam"],mouth,dental)
        patches[key]=(mouth,piece)
    # Records include a gutter below and to the right of each patch, so Godot's
    # bilinear filtering cannot pick up color from the next animation frame.
    atlas=Image.new("RGBA",(max(eyes[2],mouth[2])+2,2*(eyes[3]+2)+4*(mouth[3]+2)))
    frames={};y=0
    for key,(box,piece) in patches.items():
        clipped=Image.fromarray(np.minimum(np.asarray(piece.getchannel("A")),
            np.asarray(neutral.getchannel("A").crop((box[0],box[1],box[0]+box[2],box[1]+box[3])))))
        piece.putalpha(clipped)
        atlas.paste(piece,(0,y))
        frames[key]={"atlas_region":[0,y,box[2],box[3]],"source_origin":list(box[:2])}
        y+=box[3]+2
    asset=folder/(name+"-face-atlas.png");atlas.save(asset,optimize=True)
    seam=settings["seam"];center_x=(seam[0][0]+seam[-1][0])*.5
    manifest={"base":source.name,"atlas":asset.name,"source":"assets/characters/"+name+"/sprites/"+source.name,
      "source_sha256":art.sha(source),"size":[width,height],"origin":"top_left","foot_anchor":[width//2,height],
      "eye_centers":settings["centers"],"mouth_center":[round(center_x),round(float(art.line(seam,center_x)))],
      "frames":frames,"cue_frames":CUES,"sha256":{source.name:art.sha(source),asset.name:art.sha(asset)}}
    (folder/"sprite.json").write_text(json.dumps(manifest,indent=2)+"\n")
    if review:
        review.mkdir(exist_ok=True,parents=True)
        aw,ah=360,290
        x0=eyes[0]-13; y0=eyes[1]-14; x1=eyes[0]+eyes[2]+13; y1=mouth[1]+mouth[3]+3
        out=Image.new("RGB",(aw*4,ah+25),"#343638")
        draw=ImageDraw.Draw(out)
        for i,(key,label) in enumerate(((None,"Rest"),("blink_closed","Closed blink"),("mouth_open","Open"),("mouth_round","Rounded"))):
            pose=neutral.copy()
            if key:
                pos,piece=patches[key];pose.alpha_composite(piece,pos[:2])
            fg=pose.crop((x0,y0,x1,y1)).resize((aw,ah),Image.Resampling.LANCZOS)
            out.paste(fg,(aw*i,0),fg)
            draw.text((aw*i+7,ah+6),label,fill="white")
        out.save(review/(name+"-expressions.jpg"),quality=95)
    print(name,atlas.size,asset.stat().st_size,manifest["mouth_center"])

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--review",type=Path);args=p.parse_args()
    for name in FACES:prepare(name,args.review)
