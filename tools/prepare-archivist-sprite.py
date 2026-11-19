"""Prepare the 2D Archivist from the approved original. Requires Pillow, NumPy and SciPy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, map_coordinates
from scipy.interpolate import PchipInterpolator

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=ROOT/"assets/concepts/characters/archivist-front-modeling-v1.png"
DEST=ROOT/"assets/characters/archivist/sprites"
EYES=(440,121,144,56)
MOUTH=(464,181,96,48)
SCALE=6

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cutout(source, vision):
    rgb=np.asarray(source.convert("RGB"),dtype=np.float32)
    alpha=np.asarray(vision.convert("RGBA").getchannel("A"),dtype=np.float32)
    alpha=np.clip((alpha-3.)*255./249.,0,255)
    nearest=distance_transform_edt(alpha>1,return_distances=False,return_indices=True)
    back=rgb[nearest[0],nearest[1]]
    a=alpha[:,:,None]/255
    # Unmix the original gray ground only along the soft silhouette.
    color=np.clip(back+(rgb-back)/np.maximum(.18,a),0,255)
    color=np.where(a>.985,rgb,color)
    color=np.where(a==0,0,color)
    return Image.fromarray(np.dstack((np.rint(color),np.rint(alpha))).astype("uint8"))

def pixels(box):
    x,y,w,h=box
    yy,xx=np.mgrid[0:h*SCALE,0:w*SCALE]
    return x+(xx+.5)/SCALE-.5,y+(yy+.5)/SCALE-.5

def sample(rgb,x,y):
    return np.stack([map_coordinates(rgb[:,:,channel],[y,x],order=1,mode="nearest")
                     for channel in range(3)],axis=-1)

def line(points,x):
    pts=np.asarray(points)
    return PchipInterpolator(pts[:,0],pts[:,1])(np.clip(x,pts[0,0],pts[-1,0]))

def image_patch(rgb,box,edit):
    x,y=pixels(box)
    base=sample(rgb,x,y)
    result=edit(x,y,base)
    image=Image.fromarray(np.rint(np.clip(result,0,255)).astype("uint8"))
    patch=image.resize(box[2:],Image.Resampling.LANCZOS).convert("RGBA")
    # Only modified facial pixels belong to a patch. Leave the cutout and all
    # unmodified features untouched, including the clear area beside the jaw.
    changed=np.max(np.abs(result-base),axis=2)>0.18
    coverage=Image.fromarray(changed.astype("uint8")*255).resize(box[2:],Image.Resampling.BOX)
    patch.putalpha(coverage.point(lambda a:min(255,2*a)))
    return patch

# The upper and lower landmarks follow the approved portrait, in full-canvas pixels.
UPPER=[
 [(456,142),(462,139.0),(469,135.9),(474,135.8),(480,137.1),(486,140.9),(491,146.8),(494,153)],
 [(530,153),(534,147.4),(538,141.7),(544,137.4),(550,135.4),(556,135.6),(561,137.5),(567,141.9)]]
LOWER=[
 [(456,142),(461,146.6),(467,151.3),(473,153.5),(480,154.2),(486,153.9),(491,153.3),(494,153)],
 [(530,153),(535,153.2),(542,154.2),(549,153.8),(555,152.7),(562,148.6),(567,141.9)]]

def blink(rgb,weight,upper_lids=UPPER,lower_lids=LOWER,box=EYES,human_lids=False):
    def deform(x,y,base):
        dst=base.copy()
        for upper,lower in zip(upper_lids,lower_lids):
            up=line(upper,x); down=line(lower,x); h=np.maximum(0,down-up)
            valid=(x>=upper[0][0])&(x<=upper[-1][0])
            end=up+.82*h*weight
            foot=down-.19*h*weight
            ratio=np.clip((y-up)/np.maximum(end-up,.1),0,1)
            # The donor band lies directly above the original eyelash. It
            # contains the intact pearl shading from the same side of the face.
            donor=up-1.65-(1-ratio)*np.minimum(3.8,.27*h)
            skin=sample(rgb,x,donor)
            if human_lids:
                # Lashes occupy several rows in the higher-resolution seated
                # portraits. Reconstruct the lid from clear skin above them.
                samples=[]
                for offset in (-2.8,-1.4,0,1.4,2.8):
                    u=x+offset
                    source_y=line(upper,u)-3.7-(1-ratio)*np.minimum(3.3,.24*h)
                    samples.append(sample(rgb,u,source_y))
                skin=np.median(samples,axis=0)
            lash=np.minimum.reduce([sample(rgb,x,up+v) for v in (-1.1,-.35,.55)])*.86
            band=np.exp(-((y-end)/.82)**2)[:,:,None]
            skin=skin*(1-band*.96)+lash*(band*.96)
            upper_mask=np.clip(np.minimum(y-up+(3.1 if human_lids else 1.65),end-y+.68),0,1)*valid
            below=np.clip((down-y)/np.maximum(down-foot,.1),0,1)
            lower_skin=sample(rgb,x,down+1.1+(1-below)*1.6)
            lower_mask=np.clip(np.minimum(y-foot+.4,down-y+.9),0,1)*valid
            dst=dst*(1-lower_mask[:,:,None])+lower_skin*lower_mask[:,:,None]
            dst=dst*(1-upper_mask[:,:,None])+skin*upper_mask[:,:,None]
        return dst
    return image_patch(rgb,box,deform)

MOUTH_EDGE=[(493,202.8),(497,203.1),(503,202.9),(508,202.6),
            (512,203.0),(516,202.6),(521,202.8),(527,203.1),(532,202.5)]

def lips(rgb,openness,rounding,spread,edge=MOUTH_EDGE,box=MOUTH,dental=None):
    center=(edge[0][0]+edge[-1][0])*.5
    radius=(edge[-1][0]-edge[0][0])*.5
    scale=radius/19.5
    def deform(x,y,base):
        scale_x=1+spread-rounding*.14
        xx=center+(x-center)/scale_x
        mid=line(edge,xx)
        across=np.clip((xx-center)/radius,-1,1)
        span=np.maximum(0,1-across**2)**.80
        upper=mid-openness*.20*span
        lower=mid+openness*.80*span
        # Pull pixels from each original lip and gently fade the displacement
        # through the philtrum and chin. The skin outside the patch stays fixed.
        above=y<upper
        delta=np.where(above,(mid-upper)*np.exp(-np.maximum(upper-y,0)/(4.3*scale)),
                       -(lower-mid)*np.exp(-np.maximum(y-lower,0)/(5.6*scale)))
        near=np.exp(-(np.maximum(0,np.abs(x-center)-13*scale)/(10*scale))**2-(np.abs(y-mid)/(9*scale))**2)
        source_x=x+(xx-x)*near
        lip_color=sample(rgb,source_x,y+delta)
        # Derive the mouth color from the actual lip seam, with depth occlusion.
        t=np.clip((y-upper)/np.maximum(.1,lower-upper),0,1)
        seam=sample(rgb,xx,mid)
        interior=seam*(.21+.19*t**2)[:,:,None]+np.array((7.,1.,3.))
        mucosa=np.exp(-((t-.87)/.21)**2)*(1-across**2)*openness/8
        interior+=mucosa[:,:,None]*np.array((20.,6.,7.))
        if dental is not None:
            # Only a slender, shadowed dental edge reads at a conversational
            # opening. Match the portrait's lighting using the source sclera.
            height=np.clip((openness-3.5)/5,0,1)
            upper_edge=.13+.05*(1-across**2)+.015*np.cos(across*14)
            glimpse=np.clip((upper_edge-t)*13,0,1)*np.clip((.81-np.abs(across))*5,0,1)*height
            ivory=np.asarray(dental)*np.array((.65,.61,.55))
            interior=interior*(1-glimpse[:,:,None])+ivory*glimpse[:,:,None]
        m=np.clip(np.minimum(y-upper+.4,lower-y+.4),0,1)*span**.20
        out=lip_color*(1-m[:,:,None])+interior*m[:,:,None]
        active=np.clip((1.12-np.abs((x-center)/(24*scale)))*5,0,1)*np.exp(-np.maximum(0,np.abs(y-mid)-11*scale)/(4*scale))
        if dental is not None:
            bx,by,bw,bh=box
            dist=np.minimum.reduce((x-bx,bx+bw-1-x,y-by,by+bh-1-y))
            feather=np.clip((dist-2)/(3.3*scale),0,1)
            active*=feather*feather*(3-2*feather)
        return out*active[:,:,None]+base*(1-active[:,:,None])
    return image_patch(rgb,box,deform)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--vision-mask",type=Path)
    opts=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    source=Image.open(REFERENCE).convert("RGB")
    with tempfile.TemporaryDirectory() as temporary:
        mask=opts.vision_mask or Path(temporary)/"vision.png"
        if not opts.vision_mask:
            subprocess.run([str(ROOT/".tools/bin/prepare-board-reference"),str(REFERENCE),str(mask),"0","0","1024","1536"],check=True)
        neutral=cutout(source,Image.open(mask))
    neutral.save(DEST/"archivist.png",optimize=True)
    rgb=np.asarray(source,dtype=float)
    patches={"blink_half":(EYES,0,blink(rgb,.52)),"blink_closed":(EYES,56,blink(rgb,1.0)),
             "mouth_parted":(MOUTH,112,lips(rgb,2.6,0,0)),"mouth_open":(MOUTH,160,lips(rgb,6.0,0,.02)),
             "mouth_round":(MOUTH,208,lips(rgb,6.8,.95,-.04)),"mouth_wide":(MOUTH,256,lips(rgb,3.2,0,.08))}
    atlas=Image.new("RGBA",(144,304))
    frames={}
    for key,(rect,row,piece) in patches.items():
        atlas.paste(piece,(0,row))
        frames[key]={"atlas_region":[0,row,rect[2],rect[3]],"source_origin":list(rect[:2])}
    atlas.save(DEST/"archivist-face-atlas.png",optimize=True)
    for key,out in (("blink_closed","archivist-blink.png"),("mouth_open","archivist-speaking.png")):
        rect,_,patch=patches[key]
        variant=neutral.copy();variant.alpha_composite(patch,rect[:2]);variant.save(DEST/out,optimize=True)
    manifest={"source":"assets/concepts/characters/archivist-front-modeling-v1.png","source_sha256":sha(REFERENCE),
              "size":[1024,1536],"origin":"top_left","foot_anchor":[512,1486],
              "eye_centers":[[478,146],[546,145]],"mouth_center":[512,203],
              "base":"archivist.png","atlas":"archivist-face-atlas.png","frames":frames,
              "cue_frames":{"X":None,"A":None,"B":"mouth_parted","C":"mouth_wide","D":"mouth_open",
                            "E":"mouth_round","F":"mouth_round","G":"mouth_parted","H":"mouth_parted"},
              "full_canvas_examples":{"blink_closed":"archivist-blink.png","mouth_open":"archivist-speaking.png"}}
    manifest["sha256"]={p.name:sha(p) for p in (DEST/"archivist.png",DEST/"archivist-face-atlas.png",DEST/"archivist-blink.png",DEST/"archivist-speaking.png")}
    (DEST/"sprite.json").write_text(json.dumps(manifest,indent=2)+"\n")
if __name__=="__main__":main()
