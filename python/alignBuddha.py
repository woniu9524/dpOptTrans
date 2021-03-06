import numpy as np
from scipy.linalg import inv
from js.data.plyParse import PlyParse
import os.path, re, json
import subprocess as subp
from js.geometry.rotations import Quaternion
from js.utils.plot.colors import colorScheme
from helpers import *

def AlphaBlend(rgbs, color, alpha, toGrey=False):
  if toGrey:
    grey = np.mean(rgbs,axis=1)
    rgbs[:,0] = grey
    rgbs[:,1] = grey
    rgbs[:,2] = grey
  rgbs *= alpha
  rgbs += (1.-alpha)* np.resize(color,rgbs.shape)
  return rgbs

def PlotColoredPc(pc, rgb):
  #http://stackoverflow.com/questions/18537172/specify-absolute-colour-for-3d-points-in-mayavi
  rgba = np.concatenate((rgb.astype(np.uint8),np.ones((rgb.shape[0],1),dtype=np.uint8)*255),axis=1)
  rgba[:,[1, 2]] = rgba[:,[2, 1]]
  scalars = np.arange(rgb.shape[0])
  pts=mlab.points3d(pc[:,0], pc[:,1], pc[:,2], scalars, mode="point")
  pts.glyph.color_mode = 'color_by_scalar' # Color by scalar
  # Set look-up table and redraw
  pts.module_manager.scalar_lut_manager.lut.table = rgba
  mlab.draw()

def PlotShadedColoredPc(pc, rgb, color, alpha):
  rgb = AlphaBlend(rgb, color, alpha, toGrey=True)
  PlotColoredPc(pc, rgb)

def logDeviations(fRes,pathGtA,pathGtB,q_ba,t_ba,dt,algo):
  # loaded transformation is T_wc
  q_gtA,t_gtA,_ = LoadTransformation(pathGtA)
  q_gtB,t_gtB,_ = LoadTransformation(pathGtB)
  dq_gt = q_gtB.inverse().dot(q_gtA)
  dt_gt = q_gtB.inverse().rotate(t_gtA - t_gtB)
  dAngDeg = q_ba.angleTo(dq_gt)*180./np.pi
  dTrans = np.sqrt(((t_ba-dt_gt)**2).sum())
  print 'q_gtA', q_gtA
  print 'q_gtB', q_gtB
  print 'dq_gt', dq_gt
  print 'dt_gt', dt_gt
  print 'q_ba', q_ba
  print 't_ba', t_ba
  print "Angle to GT: {} deg".format(dAngDeg)
  print "Translation deviation to GT: {} m".format(dTrans)
  fRes.write("{} {} {} {} {} {}\n".format(algo,i-1,i,dAngDeg,dTrans,dt))
  fRes.flush()
  print "wrote results to " + fRes.name

cfgEnschede = {"name":"enschede", "lambdaS3": [60, 70, 80], "lambdaR3":0.3}
cfgBunnyZipper = {"name":"bun_zipper", "lambdaS3": [60], "lambdaR3":
    0.001, "maxLvlR3":15, "maxLvlS3":5 }

#cfgBunnyAB = {"name":"bunnyAB", "lambdaS3": [45, 60, 70, 80], "lambdaR3": 0.003}
cfgBunnyAB = {"name":"bunnyAB", "lambdaS3":
    [60,70,80], "lambdaR3": 0.001, "maxLvlR3":15, "maxLvlS3":15}

cfgBunny = {"name":"bunny", "lambdaS3": [60, 70, 80], "lambdaR3": 0.001,
    "maxLvlR3":15, "maxLvlS3":5}
cfgLymph = {"name":"lymph", "lambdaS3": [80], "lambdaR3": 1.}
cfgBuddha = {"name":"buddha", "lambdaS3": [60,70,80], "lambdaR3": 0.0008}
cfgBuddhaRnd = {"name":"buddhaRnd", "lambdaS3": [50,60,70,80],
  "lambdaR3": 0.002}

cfgBuddhaRnd = {"name":"buddhaRnd", "lambdaS3": [60,70,80], "lambdaR3": 0.002, 
    "maxLvlR3":15, "maxLvlS3":5}
# lambdaR3 10 was good; lambdaS3 ,65,80
cfgWood= {"name":"wood", "lambdaS3": [65], "lambdaR3": 10., 
    "maxLvlR3":8, "maxLvlS3":13}


cfgDesk0 = {"name":"desk0", "lambdaS3": [65], "lambdaR3": 0.15, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}

#cfgDesk1 = {"name":"desk1", "lambdaS3": [60,70,80], "lambdaR3": 0.1, 
cfgDesk1 = {"name":"desk1", "lambdaS3": [45,65,85], "lambdaR3": 0.15, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}
cfgDesk1 = {"name":"desk1", "lambdaS3": [65], "lambdaR3": 0.2, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}

#fast?
cfgStairs = {"name":"stairs", "lambdaS3": [45], "lambdaR3": 15.,
    "maxLvlR3":10, "maxLvlS3":12, "tryMfAmbig":True } #14
# accurate?
cfgStairs = {"name":"stairs", "lambdaS3": [45,65,80], "lambdaR3": 15.,
    "maxLvlR3":10, "maxLvlS3":12, "tryMfAmbig":True } #14
cfgStairs = {"name":"stairs", "lambdaS3": [45,65,80], "lambdaR3": 3.3,
    "maxLvlR3":10, "maxLvlS3":11, "tryMfAmbig":True } #14

#fast? fails to align randys desk
cfgD458fromDesk= {"name":"D458fromDesk", "lambdaS3": [45,65,85], "lambdaR3": 0.5, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}
# accurate?
cfgD458fromDesk= {"name":"D458fromDesk", "lambdaS3": [45,65,85], "lambdaR3": 0.15, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}

cfgSingleRoom0 = {"name":"singleRoom0", "lambdaS3": [45,65,85], "lambdaR3": 0.15, 
    "maxLvlR3":10, "maxLvlS3":12, "icpCutoff": 0.1}
#cfgSingleRoom0 = {"name":"singleRoom0", "lambdaS3": [45,65,85],
cfgSingleRoom0 = {"name":"singleRoom0", "lambdaS3": [45],
    "lambdaR3": 0.3, "maxLvlR3":12, "maxLvlS3":13, "icpCutoff": 0.1 }

#fast but not accurate
cfgApartment= {"name":"apartment", "lambdaS3": [65], "lambdaR3": 2., 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":True}
cfgApartment= {"name":"apartment", "lambdaS3": [45,65,80], "lambdaR3": 1., 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":False}
#accurate
cfgApartment= {"name":"apartment", "lambdaS3": [45,65,80], "lambdaR3": 1., 
    "maxLvlR3":13, "maxLvlS3":13, "icpCutoff": 0.1, "tryMfAmbig":True}
cfgApartment= {"name":"apartment", "lambdaS3": [45,65,80], "lambdaR3": 1., 
    "maxLvlR3":13, "maxLvlS3":13, "icpCutoff": 0.1, "tryMfAmbig":False}
# try:
# Scale
cfgApartment= {"name":"apartment", "lambdaS3": [45,65,80], "lambdaR3": 1.3, 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":False,
    "scale":0.1 }
# MW Scale
cfgApartment= {"name":"apartment", "lambdaS3": [45,65,80], "lambdaR3": 1.3, 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":True,
    "scale":0.1 }
# MW
cfgApartment= {"name":"apartment", "lambdaS3": [65], "lambdaR3": 1.3, 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":True,
    "scale":0.1 }

cfgUwa = {"name":"uwa", "lambdaS3": [65], "lambdaR3": 1000., 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":True}

# Scale
cfgGazeboSummer = {"name":"gazebo_summer", "lambdaS3": [45,65,80], "lambdaR3": 7., 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.3, "tryMfAmbig":False,
    "scale":0.3 }
cfgGazeboWinter = {"name":"gazebo_winter", "lambdaS3": [45,65,80], "lambdaR3": 2.0, 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":False,
    "scale":0.1 }
cfgMountain = {"name":"mountain_plain", "lambdaS3": [45,65,80], "lambdaR3": 2.0, 
    "maxLvlR3":10, "maxLvlS3":11, "icpCutoff": 0.1, "tryMfAmbig":False,
    "scale":0.1 }

cfg = cfgEnschede
cfg = cfgLymph
cfg = cfgWood
cfg = cfgBuddha

cfg = cfgApartment

cfg = cfgBuddhaRnd
cfg = cfgD458fromDesk
cfg = cfgSingleRoom0
cfg = cfgDesk1
cfg = cfgDesk0
cfg = cfgApartment
cfg = cfgStairs
cfg = cfgBunnyAB
cfg = cfgBunny
cfg = cfgBunnyZipper
cfg = cfgUwa
cfg = cfgMountain
cfg = cfgGazeboWinter
cfg = cfgGazeboSummer

if not "tryMfAmbig" in cfg:
  cfg["tryMfAmbig"] = False

applyFFT   = False
runGoICP   = False
runGogma   = False
applyBB    = not runGoICP and not applyFFT and not runGogma
applyICP   = applyBB
applyBBEGI = False
applyMM    = False

loadCached = False
stopToShow = True
stopEveryI = 3
showTransformed =  True 
showUntransformed =False

if runGoICP or applyFFT:
  stopToShow = False

simpleTranslation = False
simpleRotation = False
useS3tessellation = True
useTpStessellation = not useS3tessellation and False
useAAtessellation = not useS3tessellation and not useTpStessellation

outputBoundsAt0 = True
loadGlobalsolutionforICP = True
useSurfaceNormalsInICP = True

print json.dumps(cfg)

qOffset = Quaternion()
pathGOGMAcfg = "/home/jstraub/workspace/research/3rdparty/gogma/build/config.txt"

if cfg["name"] == "lymph":
  pattern = "frame_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/lymph/dataset_3/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",re.sub("frame_","",os.path.split(f)[1]))))
  gt = []
if cfg["name"] == "buddha":
  pattern = "happyStandRight_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/happy_stand/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",re.sub("happyStandRight_","",os.path.split(f)[1]))))
  gt = []
if cfg["name"] == "buddhaRnd":
  pattern = "happyStandRight_[0-9]+_angle_90_translation_0.3.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/happy_stand_rnd/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub("_angle_90_translation_0.3.ply","",
      re.sub("happyStandRight_","",os.path.split(f)[1]))))
  gt = []
  scans = np.roll(scans, 7)
  print scans
#  raw_input()
#  scans2  = []
#  for scan in scans:
#    id = int(re.sub("_angle_90_translation_0.3.ply","",re.sub("happyStandRight_","",os.path.split(scan)[1])))
#    if id in [264, 288]:
#      scans2.append(scan)
#  scans = scans2
#  scans = scans[:5]
  pathGOGMAcfg = "/home/jstraub/workspace/research/3rdparty/gogma/build/configHappyBuddha.txt"
if cfg["name"] == "uwa":
  gt = []
  scans = ['../data/uwa/scenes/rs2.ply', '../data/uwa/scenes/rs2.ply']
  scans = ['../data/uwa/models/T-rex_high_ascii.ply', '../data/uwa/models/T-rex_high_ascii.ply']
  scans = ['../data/uwa/scenes/rs2.ply', '../data/uwa/models/T-rex_high_ascii.ply']
  scans = ['../data/uwa/scenes/rs9.ply', '../data/uwa/models/cheff.ply']
  print scans
if cfg["name"] == "bunny":
  pattern = "bun[0-9]+_angle_90_translation_0.3.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/bunny_rnd/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub("_angle_90_translation_0.3.ply","",re.sub("bun","",os.path.split(f)[1]))))
  gt = []
if cfg["name"] == "bun_zipper":
  scans = ['../data/bunny_rnd/bun_zipper.ply',
      '../data/bunny_rnd/bun_zipper_angle_90_translation_0.3.ply']
  #gt = ['../data/bunny_rnd/bun_zipper_angle_90_translation_0.3.ply_TrueTransformation_angle_90_translation_0.3.csv']
  gt = []
if cfg["name"] == "bunnyAB":
  scans = ['../data/bunny_rnd/bun000_angle_90_translation_0.3.ply',
      '../data/bunny_rnd/bun045_angle_90_translation_0.3.ply']
  gt = ['../data/bunny_rnd/bun000_angle_90_translation_0.3_TrueTransformation.csv',
  '../data/bunny_rnd/bun045_angle_90_translation_0.3_TrueTransformation.csv']
  qOffset = Quaternion(w=np.cos(0.5*np.pi/4.), x=0, y=0,
      z=-np.sin(0.5**np.pi/4.)/(np.pi/4.))
if cfg["name"] == "enschede":
  scans = ['../data/enschede_rnd/0021770_2_inv_depth_map_gray.ply',
    '../data/enschede_rnd/0021771_2_inv_depth_map_gray_angle_50_translation_10.ply',
    '../data/enschede_rnd/0021772_2_inv_depth_map_gray_angle_50_translation_10.ply']
  gt=[]
if cfg["name"] == "stairs":
  pattern = "HokuyoPcNormals_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/stairs/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_","",os.path.split(f)[1]))))
#  scans = [
#      os.path.abspath('../data/stairs/HokuyoPcNormals_1.ply'),
#      os.path.abspath('../data/stairs/HokuyoPcNormals_2.ply')]
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/stairs/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
#  scans = scans[:3]
#  gt = gt[:3]
  print scans
  print gt 
if cfg["name"] == "apartment":
  pattern = "HokuyoPcNormals_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/apartment/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_","",os.path.split(f)[1]))))
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/apartment/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
#  gt = gt[16:]
#  scans = scans[16:]
#  gt = gt[35:39]
#  scans = scans[35:39]
  gt = gt[:33]
  scans = scans[:33]
  print scans
  print gt
  pathGOGMAcfg = "/home/jstraub/workspace/research/3rdparty/gogma/build/configApartment.txt"
if cfg["name"] == "gazebo_summer":
  pattern = "HokuyoPcNormals_0_2_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/gazebo_summer/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_0_2_","",os.path.split(f)[1]))))
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/gazebo_summer/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
#  gt = gt[16:20]
#  scans = scans[16:20]
#  gt = gt[:4]
#  scans = scans[:4]
#  gt = gt[35:39]
#  scans = scans[35:39]
#  gt = gt[:33]
#  scans = scans[:33]
  print scans
  print gt
  pathGOGMAcfg = "/home/jstraub/workspace/research/dpOptTrans/python/configGazebo.txt"
if cfg["name"] == "gazebo_winter":
  pattern = "HokuyoPcNormals_0_2_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/gazebo_winter/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_0_2_","",os.path.split(f)[1]))))
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/gazebo_winter/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
#  gt = gt[16:19]
#  scans = scans[16:19]
#  gt = gt[:4]
#  scans = scans[:4]
#  gt = gt[35:39]
#  scans = scans[35:39]
#  gt = gt[:33]
#  scans = scans[:33]
  print scans
  print gt
  pathGOGMAcfg = "/home/jstraub/workspace/research/dpOptTrans/python/configGazebo.txt"
if cfg["name"] == "mountain_plain":
  pattern = "HokuyoPcNormals_0_2_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/mountain_plain/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_0_2_","",os.path.split(f)[1]))))
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/mountain_plain/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
#  gt = gt[16:20]
#  scans = scans[16:20]
  gt = gt[:3]
  scans = scans[:3]
#  gt = gt[35:39]
#  scans = scans[35:39]
#  gt = gt[:33]
#  scans = scans[:33]
  print scans
  print gt
  pathGOGMAcfg = "/home/jstraub/workspace/research/3rdparty/gogma/build/configApartment.txt"
if cfg["name"] == "wood":
  pattern = "HokuyoPcNormals_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("../data/wood_summer/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("HokuyoPcNormals_","",os.path.split(f)[1]))))
  gt=[]
  pattern = "pose_[0-9]+.csv$"
  for root, dirs, files in os.walk("../data/wood_summer/"):
    for f in files:
      if re.search(pattern, f):
        gt.append(os.path.join(root, f))
  gt = sorted(gt, key=lambda f: 
    int(re.sub(".csv","",
      re.sub("pose_","",os.path.split(f)[1]))))
  print scans
  print gt
if cfg["name"] == "desk1":
  pattern = "frame_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("/data/vision/fisher/expres1/jstraub/optRotTransCVPR2017_KFs/desk1Wrgb/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("frame_","",os.path.split(f)[1]))))
  print scans
  gt=[]
if cfg["name"] == "desk0":
  pattern = "frame_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("/data/vision/fisher/expres1/jstraub/optRotTransCVPR2017_KFs/desk0Wrgb/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("frame_","",os.path.split(f)[1]))))
  scans = scans[13::2]
  print scans
  gt=[]
if cfg["name"] == "singleRoom0":
  pattern = "frame_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("/data/vision/fisher/expres1/jstraub/optRotTransCVPR2017_KFs/singleRoom0Wrgb/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("frame_","",os.path.split(f)[1]))))
  scans = scans[6:]
  print scans
  gt=[]
if cfg["name"] == "D458fromDesk":
  pattern = "frame_[0-9]+.ply$"
  scans = []
  for root, dirs, files in os.walk("/data/vision/fisher/expres1/jstraub/optRotTransCVPR2017_KFs/32-D458_fromDesk/"):
    for f in files:
      if re.search(pattern, f):
        scans.append(os.path.join(root, f))
  scans = sorted(scans, key=lambda f: 
    int(re.sub(".ply","",
      re.sub("frame_","",os.path.split(f)[1]))))
#  scans = scans[:4]
  print scans
#  scans = [
#      os.path.abspath('../data/stairs/HokuyoPcNormals_1.ply'),
#      os.path.abspath('../data/stairs/HokuyoPcNormals_2.ply')]
  gt=[]

print scans
colors = colorScheme("label")

if showUntransformed or showTransformed:
  import mayavi.mlab as mlab

#figm = mlab.figure(bgcolor=(1,1,1))
#ply = PlyParse();
#ply.parse(scans[0])
#pc = ply.getPc()
#rgb = ply.rgb
#PlotShadedColoredPc(pc, rgb, np.array([255,0,0]),0.6)
#mlab.show(stop=True)


if showUntransformed:
  figm = mlab.figure(bgcolor=(1,1,1))
  for i in range(len(scans)):
    scanPath = scans[i]
    ply = PlyParse();
    ply.parse(scanPath)
    pc = ply.getPc()
    n = ply.n
    mlab.points3d(pc[:,0], pc[:,1], pc[:,2], mode="point",
        color=colors[i%len(colors)])
    mlab.quiver3d(pc[:,0], pc[:,1], pc[:,2],n[:,0], n[:,1], n[:,2],
        color=colors[(2+i)%len(colors)],mask_points=20,
        line_width=1., scale_factor=0.01)
    print pc.max()
    print pc.min()
#    mlab.points3d(n[:,0]+i*2.3, n[:,1], n[:,2], mode="point",
#        color=colors[(2+i)%len(colors)])

  mlab.show(stop=True)

prefix = "{}_{}".format(cfg["name"],int(np.floor(time.time()*1e3)))

if len(gt) > 0:
  fRes = open(prefix+"resultsVsGrountruth.csv","w")
  fRes.write("algo idFrom idTo dAngDeg dTrans dTimeSec\n")
  fRes.write(json.dumps(cfg)+"\n")
  fRes.flush()

alpha = 0.8 # 0.7
W_T_B = np.eye(4)
for i in range(1,len(scans)):
  scanApath = scans[i-1]
  scanBpath = scans[i]
  nameA = os.path.splitext(os.path.split(scanApath)[1])[0]
  nameB = os.path.splitext(os.path.split(scanBpath)[1])[0]
  transformationPath = '{}_{}.csv'.format(nameA, nameB)
  transformationPathBB = '{}_{}_BB.csv'.format(nameA, nameB)
  transformationPathBBEGI = '{}_{}_BBEGI.csv'.format(nameA, nameB)
  transformationPathICP = '{}_{}_ICP.csv'.format(nameA, nameB)
  transformationPathFFT = '{}_{}_FFT.csv'.format(nameA, nameB)
  transformationPathMM = '{}_{}_MM.csv'.format(nameA, nameB)
  transformationPathGoICP = '{}_{}_GoICP.csv'.format(nameA, nameB)
  transformationPathGogma = '{}_{}_Gogma.csv'.format(nameA, nameB)

  if i == 1:
    plyA = PlyParse();
    plyA.parse(scanApath)
    pcA = plyA.getPc()
    if showTransformed:
      figm = mlab.figure(bgcolor=(1,1,1))
      if plyA.rgb.sum() > 0:
        print colors[0]
        PlotShadedColoredPc(pcA, plyA.rgb, 255*np.array(colors[0]),alpha)
      else:
        mlab.points3d(pcA[:,0], pcA[:,1], pcA[:,2], mode="point",
          color=colors[0])

  if runGogma:
    q_ba,t_ba,q_baGlobal,t_baGlobal,dt,success = RunGogma(scanApath, scanBpath,
        transformationPathGogma, pathGOGMAcfg)
    if i-1 < len(gt):
      logDeviations(fRes, gt[i-1], gt[i], q_baGlobal,t_baGlobal,dt,"GOGMAonly")
      logDeviations(fRes, gt[i-1], gt[i], q_ba,t_ba,dt,"GOGMA")

  if runGoICP:
    q_ba,t_ba,dt,success = RunGoICP(scanApath, scanBpath,
        transformationPathGoICP, 100)

    if i-1 < len(gt):
      logDeviations(fRes, gt[i-1], gt[i], q_ba,t_ba,dt,"GoICP")

  if applyBB:
    if loadCached and os.path.isfile(transformationPathBB):
      print "found transformation file and using it "+transformationPathBB
    else:
      q_ba,t_ba,Ks,dt,_ = RunBB(cfg, scanApath, scanBpath,
          transformationPathBB, TpSmode=useTpStessellation,
          outputBoundsAt0=outputBoundsAt0,
          AAmode=useAAtessellation,
          simpleTranslation=simpleTranslation,
          simpleRotation=simpleRotation,
          scale=cfg["scale"],
          tryMfAmbig=cfg["tryMfAmbig"])
    transformationPath = transformationPathBB

    if i-1 < len(gt):
      logDeviations(fRes, gt[i-1], gt[i], q_ba,t_ba,dt,"BB")

  if applyBBEGI:
    if loadCached and os.path.isfile(transformationPathBBEGI):
      print "found transformation file and using it "+transformationPathBBEGI
    else:
      q_ba,t_ba,dt,_ = RunBB(cfg, scanApath, scanBpath,
          transformationPathBBEGI, EGImode=True, TpSmode=
          useTpStessellation)
    transformationPath = transformationPathBBEGI

  if applyFFT:
    if loadCached and os.path.isfile(transformationPathFFT):
      print "found transformation file and using it " +transformationPathFFT
    else:
      q_ba,t_ba,dt,_ = RunFFT(scanApath, scanBpath, transformationPathFFT)
      with open(transformationPathFFT,'w') as f: 
        f.write("qw qx qy qz tx ty tz\n")
        f.write("{} {} {} {} {} {} {}\n".format(
          q_ba.q[0],q_ba.q[1],q_ba.q[2],q_ba.q[3],t_ba[0],t_ba[1],t_ba[2]))
    transformationPath = transformationPathFFT

    if i-1 < len(gt):
      logDeviations(fRes, gt[i-1], gt[i], q_ba,t_ba,dt,"FFT")

  if applyMM:
    if loadCached and os.path.isfile(transformationPathMM):
      print "found transformation file and using it " +transformationPathMM
    else:
      q_ba,t_ba,dt,_ = RunMM(scanApath, scanBpath, transformationPathMM)
    transformationPath = transformationPathMM

  if applyICP:
    if loadCached and os.path.isfile(transformationPathICP):
      print "found transformation file and using it "+transformationPathICP
    else:
      if "icpCutoff" in cfg:
        q_ba,t_ba,dt,_ = RunICP(scanApath, scanBpath, transformationPathICP,
            useSurfaceNormalsInICP, transformationPath,
            cutoff=cfg["icpCutoff"])
      else:
        q_ba,t_ba,dt,_ = RunICP(scanApath, scanBpath, transformationPathICP,
            useSurfaceNormalsInICP, transformationPath)
    transformationPath = transformationPathICP
    if i-1 < len(gt):
      logDeviations(fRes, gt[i-1], gt[i], q_ba,t_ba,dt, "ICP")

#  q_ba,t_ba = LoadTransformation(transformationPath)
  R_ba = q_ba.toRot().R
  print "R_ba", R_ba
  A_T_B = np.eye(4)
  A_T_B[:3,:3] = R_ba.T
  A_T_B[:3,3] = -R_ba.T.dot(t_ba)
  W_T_B = W_T_B.dot(A_T_B)

  if showTransformed:
    plyB = PlyParse();
    plyB.parse(scanBpath)
    pcB = plyB.getPc()
    R_wb = W_T_B[:3,:3]
    t_wb = W_T_B[:3,3]
    pcB = (1.001*R_wb.dot(pcB.T)).T + t_wb
    if  plyB.rgb.sum() > 0:
      PlotShadedColoredPc(pcB, plyB.rgb, 255*np.array(colors[i%len(colors)]),alpha)
    else:
      mlab.points3d(pcB[:,0], pcB[:,1], pcB[:,2], mode="point",
          color=colors[i%len(colors)])
    if stopToShow and i%stopEveryI == 0:
      mlab.show(stop=True)
print "Done!"
if len(gt) > 0:
  fRes.close()
if showTransformed or showUntransformed:
  mlab.show(stop=True)
