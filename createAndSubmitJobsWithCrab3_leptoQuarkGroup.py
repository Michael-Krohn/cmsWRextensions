#!/usr/bin/env python

import subprocess
import os
import sys
import string
from optparse import OptionParser
import re
from datetime import datetime
import shutil
import math
from multiprocessing import Process,Queue
try:
  from CRABClient.UserUtilities import config, getUsernameFromSiteDB
except ImportError:
  print
  print 'ERROR: Could not load CRABClient.UserUtilities.  Please source the crab3 setup:'
  print 'source /cvmfs/cms.cern.ch/crab3/crab.sh'
  exit(-1)
# now we should be able to import all the crab stuff
from CRABAPI.RawCommand import crabCommand
from httplib import HTTPException


# this prints a bunch of ugly stuff. just check to make sure user has sourced the crab setup first, as above
# first setup the crab stuff by "sourcing" the crab3 setup script if needed
# NB: env only prints exported variables.
# use 'set -a && source [script] && env' to export all vars
#if not 'crab3' in sys.path:
#  command = ['bash', '-c', 'set -a && source /cvmfs/cms.cern.ch/crab3/crab.sh && env']
#  proc = subprocess.Popen(command, stdout = subprocess.PIPE)
#  for line in proc.stdout:
#    (key, _, value) = line.partition("=")
#    os.environ[key] = value.strip('\n') # without this, things get messed up
#    # if it's the python path, update the sys.path
#    if key=='PYTHONPATH':
#      valueSplit = value.split(':')
#      for v in valueSplit:
#        sys.path.append(v)
#  proc.communicate()
#  newSysPath = sys.path

# Define valid global tags by dataset as noted here:
#    https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBookMiniAOD
globalTagsByDataset = {}
# latest miniaod v2
globalTagsByDataset['Run2015C_25ns-05Oct2015-v*'] = '74X_dataRun2_reMiniAOD_v2'
globalTagsByDataset['Run2015D-05Oct2015-v*'] = '74X_dataRun2_reMiniAOD_v2'
globalTagsByDataset['Run2015D-PromptReco-v4'] = '74X_dataRun2_reMiniAOD_v2'
globalTagsByDataset['RunIISpring15MiniAODv2*'] = '74X_mcRun2_asymptotic_v5'
globalTagsByDataset['RunIISpring16MiniAODv2*'] = '80X_mcRun2_asymptotic_2016_miniAODv2_v1'
#globalTagsByDataset['RunIISpring16MiniAODv2*withHLT*'] = '80X_mcRun2_asymptotic_2016_miniAODv2_v1'
globalTagsByDataset['RunIISummer16MiniAODv2*'] = '80X_mcRun2_asymptotic_2016_TrancheIV_v8'
globalTagsByDataset['Run2016H-Prompt*'] = '80X_dataRun2_Prompt_v16'
globalTagsByDataset['Run2016B-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
globalTagsByDataset['Run2016C-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
globalTagsByDataset['Run2016D-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
globalTagsByDataset['Run2016E-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
globalTagsByDataset['Run2016F-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
globalTagsByDataset['Run2016G-23Sep2016*'] = '80X_dataRun2_2016SeptRepro_v4'
# reMiniAOD
globalTagsByDataset['Run2016B-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016C-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016D-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016E-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016F-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016G-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'
globalTagsByDataset['Run2016H-03Feb2017*'] = '80X_dataRun2_2016SeptRepro_v7'

xyCorrsByDataset = {}
xyCorrsByDataset['RunIISummer16MiniAODv2*'] = 'multPhiCorr_MC_DY_sumPT_80X'
xyCorrsByDataset['Run2016B-03Feb2017*'] = 'multPhiCorr_Data_BCDEF_80X'
xyCorrsByDataset['Run2016C-03Feb2017*'] = 'multPhiCorr_Data_BCDEF_80X'
xyCorrsByDataset['Run2016D-03Feb2017*'] = 'multPhiCorr_Data_BCDEF_80X'
xyCorrsByDataset['Run2016E-03Feb2017*'] = 'multPhiCorr_Data_BCDEF_80X'
xyCorrsByDataset['Run2016F-03Feb2017*'] = 'multPhiCorr_Data_BCDEF_80X'
xyCorrsByDataset['Run2016G-03Feb2017*'] = 'multPhiCorr_Data_GH_80X'
xyCorrsByDataset['Run2016H-03Feb2017*'] =    'multPhiCorr_Data_GH_80X'

# to feed additional files into the crab sandbox
additionalInputFiles = []
rootTupleTestDir = os.getenv('CMSSW_BASE')+'/src/Leptoquarks/RootTupleMakerV2/test/'
# just feed both in, even though we only need one at a time
#additionalInputFiles.append(rootTupleTestDir+'Summer16_23Sep2016V4_MC.db')
#additionalInputFiles.append(rootTupleTestDir+'Summer16_23Sep2016AllV4_DATA.db')

def crabSubmit(config):
    try:
        crabCommand('submit', config = config)
    except HTTPException, hte:
      print '-----> there was a problem. see below.'
      print hte.headers
      print 'quit here'
      q.put(-1)
    q.put(0)
    
def validateOptions(options):
  error = False
  if options.localStorageDir is None:
    error = True
  elif options.inputList is None:
    error = True
  elif options.cmsswCfg is None:
    error = True
  if error:
    print 'You are missing one or more required options: d, i, c'
    parser.print_help()
    exit(-1)
  if options.prevJsonFile is not None and options.jsonFile is None:
    print 'It does not make sense to specify a previously used/analyzed JSON file without specifying a new JSON file, since with this option specified, the difference between the new and old JSON is taken as the lumi mask.'
    exit(-1)


def makeDirAndCheck(dir):
  if not os.path.exists(dir):
    os.makedirs(dir)
  else:
    # in practice, this doesn't happen because of the seconds in the name, but always good to check
    print 'ERROR: directory %s already exists. Not going to overwrite it.' % dir
    exit(-2)


##############################################################
# RUN
##############################################################
#---Option Parser
#--- TODO: WHY PARSER DOES NOT WORK IN CMSSW ENVIRONMENT? ---#
usage = "Usage: %prog [options] "
#XXX TODO FIX/UPDATE THIS MESSAGE
usage+="\nSee https://twiki.cern.ch/twiki/bin/view/CMS/ExoticaLeptoquarkShiftMakeRootTuplesV22012 for more details "
usage+="\nExample1 (NORMAL MODE): %prog -d `pwd`/RootNtuple -i inputList.txt -c rootTupleMaker_CRAB_DATA_2012_53X_cfg.py "
usage+="\nExample2 (NORMAL MODE + RUN SELECTION): %prog -d `pwd`/RootNtuple -i inputList.txt -c rootTupleMaker_CRAB_DATA_2012_53X_cfg.py -r 132440-200000 "
usage+="\nExample3 (JSON MODE): %prog -d `pwd`/RootNtuple -i inputList.txt -c rootTupleMaker_CRAB_DATA_2012_53X_cfg.py -j [JSON.txt or URL, https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions12/8TeV/Prompt/Cert_190456-208686_8TeV_PromptReco_Collisions12_JSON.txt]"
usage+="\nExample4 (PREV JSON MODE): %prog -d `pwd`/RootNtuple -i inputList.txt -c rootTupleMaker_CRAB_DATA_2012_53X_cfg.py -j [JSON.txt or URL, https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions12/8TeV/Prompt/Cert_190456-208686_8TeV_PromptReco_Collisions12_JSON.txt] -p [lumiSummary.json from crab report from previous processing of same dataset]"

parser = OptionParser(usage=usage)

parser.add_option("-d", "--localStorageDir", dest="localStorageDir",
                  help="the directory localStorageDir is where the local job info is kept",
                  metavar="INDIR")

parser.add_option("-v", "--tagName", dest="tagName",
                  help="tagName of RootNTupleMakerV2",
                  metavar="TAGNAME")

parser.add_option("-i", "--inputList", dest="inputList",
                  help="list of all datasets to be used (full path required)",
                  metavar="LIST")

parser.add_option("-c", "--cfg", dest="cmsswCfg",
                  help="CMSSW template cfg",
                  metavar="CMSSWCFG")

parser.add_option("-e", "--eosDir", dest="eosDir",
                  help="EOS directory (start with /store...) to store files (used for Data.outLFNDirBase); otherwise EXO LJ group dir used with userName",
                  metavar="EOSDIR")

parser.add_option("-j", "--json", dest="jsonFile",
                  help="JSON file with selected lumi sections",
                  metavar="JSONFILE")

parser.add_option("-r", "--run range", dest="runRange",
                  help="selected run range",
                  metavar="RUNRANGE")

parser.add_option("-p", "--previousJSON json", dest="prevJsonFile",
                  help="previous lumiSummary.json from crab",
                  metavar="PREVJSON")

(options, args) = parser.parse_args()

# validate options
validateOptions(options)

# time: YYYYMMDD_HHMMSS
date = datetime.now()
#dateString = date.strftime("%Y%m%d_%H%M%S")
# I like this better, but does it break anything?
dateString = date.strftime("%Y%b%d_%H%M%S")

# find tag name if not given
if options.tagName==None:
  print 'no tagname given; will ask git for the Leptoquarks/RootTupleMakerV2 tag...',
  rootTupleMakerDir = os.getenv('CMSSW_BASE')+'/src/Leptoquarks/RootTupleMakerV2'
  proc = subprocess.Popen('revparse=`git rev-parse HEAD` && git name-rev --tags --name-only $revparse',stderr=subprocess.PIPE,stdout=subprocess.PIPE,shell=True,cwd=rootTupleMakerDir,env=dict())
  out,err = proc.communicate()
  if len(err) > 0:
    print
    print 'something went wrong trying to get the git tag:',err
    print 'please specify tagname manually with -v'
    exit(-1)
  else:
    options.tagName=out.strip()
    print 'Found tagname "'+options.tagName+'"'

topDirName = options.tagName+'_'+dateString
productionDir = options.localStorageDir+'/'+topDirName
cfgFilesDir = productionDir+'/cfgfiles'
outputDir = productionDir+'/output'
workDir = productionDir+'/workdir'
localDirs = [productionDir,cfgFilesDir,outputDir,workDir]
print 'Making local directories:'
for dir in localDirs:
  print '\t',dir
  makeDirAndCheck(dir)
print

localInputListFile = productionDir+'/inputList.txt'
shutil.copy2(options.inputList,localInputListFile)

# check if we have a proxy
proc = subprocess.Popen(['voms-proxy-info','--all'],stderr=subprocess.PIPE,stdout=subprocess.PIPE)
out,err = proc.communicate()
#print 'output----->',output
#print 'err------>',err
if 'Proxy not found' in err or 'timeleft  : 00:00:00' in out:
  # get a proxy
  print 'you have no valid proxy; let\'s get one via voms-proxy-init:'
  # this will suppress the stderr; maybe that's not so good, but I get some error messages at the moment
  #with open(os.devnull, "w") as f:
  #  proc2 = subprocess.call(['voms-proxy-init','--voms','cms','--valid','168:00'],stderr=f)
  proc2 = subprocess.call(['voms-proxy-init','--voms','cms','--valid','168:00'])

# setup general crab settings
# from https://twiki.cern.ch/twiki/bin/view/CMSPublic/CRABClientLibraryAPI
#TODO: this will work for MC. Need to update to run over data.
# notes on how the output will be stored: see https://twiki.cern.ch/twiki/bin/view/CMSPublic/Crab3DataHandling
#  <lfn-prefix>/<primary-dataset>/<publication-name>/<time-stamp>/<counter>[/log]/<file-name> 
#   LFNDirBase /                 / datasetTagName   / stuff automatically done   / from outputFile defined below
config = config()
config.General.requestName   = topDirName # overridden per dataset (= tagName_dateString)
config.General.transferOutputs = True
config.General.transferLogs = False
# We want to put all the CRAB project directories from the tasks we submit here into one common directory.
# That's why we need to set this parameter (here or above in the configuration file, it does not matter, we will not overwrite it).
config.General.workArea = productionDir
#
config.JobType.pluginName  = 'Analysis'
# feed in any additional input files
config.JobType.inputFiles = []
config.JobType.inputFiles.extend(additionalInputFiles)
config.JobType.psetName    = '' # overridden per dataset
# need to execute the user_script
#config.JobType.scriptExe = 'user_script.sh'
config.Data.inputDataset = '' # overridden per dataset
config.Data.inputDBS = 'global'
config.Data.splitting = 'FileBased' #LumiBased for data
config.Data.unitsPerJob = 1 # overridden per dataset
config.Data.totalUnits = -1 # overridden per dataset
# no publishing
config.Data.publication = False
config.Data.outputDatasetTag = 'LQ' #overridden for data
config.Data.outLFNDirBase = '/store/group/phys_exotica/leptonsPlusJets/RootNtuple/RunII/%s/' % (getUsernameFromSiteDB()) + options.tagName + '/'
#config.Data.outLFNDirBase = '/store/user/%s/' % (getUsernameFromSiteDB()) + topDirName + '/'
if options.eosDir is not None:
  # split of /eos/cms if it is there
  if options.eosDir.startswith('/eos/cms'):
    options.eosDir = options.eosDir.split('/eos/cms')[-1]
  if not options.eosDir.startswith('/store'):
    print 'eosDir must start with /eos/cms/store or /store and you specified:',options.eosDir
    print 'quit'
    exit(-1)
  outputLFN=options.eosDir
  if not outputLFN[-1]=='/':
    outputLFN+='/'
  outputLFN+=options.tagName+'/'
  if not getUsernameFromSiteDB() in outputLFN:
    outputLFN.rstrip('/')
    #config.Data.outLFNDirBase = outputLFN+'/%s/' % (getUsernameFromSiteDB()) + topDirName + '/'
    # make the LFN shorter, and in any case, the timestamp is put in by crab
    config.Data.outLFNDirBase = outputLFN+'/%s/' % (getUsernameFromSiteDB()) + options.tagName + '/'
  else:
    config.Data.outLFNDirBase = outputLFN
print 'Using outLFNDirBase:',config.Data.outLFNDirBase
config.Site.storageSite = 'T2_CH_CERN'

# look at the input list
# use DAS to find the dataset names.
# Example:
#   das_client.py --query="dataset=/LQToUE_M-*_BetaOne_TuneCUETP8M1_13TeV-pythia8/*/MINIAODSIM"
with open(localInputListFile, 'r') as f:
  for line in f:
    split = line.split()
    if len(split) <= 0:
      continue
    if '#' in split[0]: # skip comments
      #print 'found comment:',line
      continue
    if len(split) < 3:
      print 'inputList line is not properly formatted:',line
      exit(-3)
    dataset = split[0]
    nUnits = int(split[1]) #also used for total lumis for data
    nUnitsPerJob = int(split[2])
    datasetNoSlashes = dataset[1:len(dataset)].replace('/','__')
    # datasetNameNoSlashes looks like SinglePhoton__Run2015D-PromptReco-v3
    # so split to just get Run2015D-PromptReco-v3
    # and use that as the outputDatasetTag to get it into the EOS path
    primaryDatasetName = datasetNoSlashes.split('__')[0]
    secondaryDatasetName = datasetNoSlashes.split('__')[1]
    datasetName = datasetNoSlashes
    datasetName = datasetName.split('__')[0]+'__'+datasetName.split('__')[1] # get rid of part after last slash
    thisWorkDir = workDir+'/'+datasetName
    isData = 'Run201' in datasetName
    if not isData:
      datasetName=datasetName.split('__')[0]
    else:
      config.Data.outputDatasetTag=secondaryDatasetName
    # must pass isMC=false flag to cmsRun now (defaults to true)
    if isData:
      config.JobType.pyCfgParams = ['isMC=false']
    #Handle the ext1 vs non ext case specially
    if 'ext' in dataset:
      extN = dataset[dataset.find('_ext')+4]
      datasetName=datasetName+'_ext'+extN
      config.Data.outputDatasetTag='LQ_ext'+extN
    if 'backup' in dataset:
      datasetName=datasetName+'_backup'
      config.Data.outputDatasetTag='LQ_backup'
    config.Data.inputDataset = dataset
    #print 'make dir:',thisWorkDir
    makeDirAndCheck(thisWorkDir)
    outputFileNames = []
    outputFileNames.append(dataset[1:dataset.find('_Tune')])
    outputFileNames.append(dataset[1:dataset.find('_13TeV')])
    outputFileNames.append(dataset.split('/')[1])
    # get the one with the shortest filename
    outputFile = sorted(outputFileNames, key=len)[0]
    if isData:
      outputFile = outputFile + '_' + config.Data.outputDatasetTag 
    if 'ext' in dataset:
      extN = dataset[dataset.find('_ext')+4]
      outputFile = outputFile+'_ext'+extN
    if 'backup' in dataset:
      outputFile = outputFile+'_backup'
    storagePath=config.Data.outLFNDirBase+primaryDatasetName+'/'+config.Data.outputDatasetTag+'/'+'YYMMDD_hhmmss/0000/'+outputFile+'_999.root'
    #print 'will store (example):',storagePath
    #print '\twhich has length:',len(storagePath)
    if len(storagePath) > 255:
      print
      print 'we might have a problem with output path lengths too long (if we want to run crab over these).'
      print 'example output will look like:'
      print storagePath
      print 'which has length:',len(storagePath)
      print 'cowardly refusing to submit the jobs; exiting'
      exit(-2)
    else:
      print
      print 'will use storage path like:',storagePath

    if not os.path.isfile(options.cmsswCfg):
      # try relative path
      relPath = os.getenv('CMSSW_BASE')+'/src/'+options.cmsswCfg
      if os.path.isfile(relPath):
        options.cmsswCfg = relPath
      else:
        print 'cannot find CMSSW cfg:',options.cmsswCfg,'; also looked for:',relPath
        print 'quit'
        exit(-1)

    with open(options.cmsswCfg,'r') as config_file:
      config_txt = config_file.read()
    newCmsswConfig = cfgFilesDir+'/'+datasetName+'_cmssw_cfg.py'
    print 'INFO: Creating',newCmsswConfig,'...'
    
    ## check cmssw version
    #miniAODV2Support = False
    #cmsswVersion = os.getenv('CMSSW_VERSION').split('CMSSW_')[-1] # 7_4_14
    #cmsswVersionSplit = cmsswVersion.split('_')
    #if cmsswVersionSplit[0]=='7' and cmsswVersionSplit[1]=='4':
    #  # running 74X
    #  if int(cmsswVersionSplit[2]) > 12:
    #    # running 7_4_12 or higher
    #    miniAODV2Support = True

    globalTag = ''
    # for MC it will look like DYJetsToLL_M-100to200_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8__RunIISpring15MiniAODv2-74X_mcRun2_asymptotic_v2-v1
    # so split to just get RunIISpring15MiniAODv2-74X_mcRun2_asymptotic_v2-v1
    for datasetKey,tag in globalTagsByDataset.iteritems():
      #print 'try to match:',datasetKey,'and',datasetNoSlashes.split('__')[1]
      #print 'try to match:',datasetKey,'and',secondaryDatasetName
      if re.match(re.compile(datasetKey),secondaryDatasetName):
        globalTag = tag
    if globalTag=='':
      print 'WARNING: Using default global tag as specified in template cfg (are you sure it\'s the right one?)'
    else:
      print 'INFO: Overriding global tag to:',globalTag,'for dataset:',datasetName

    #Get MET phi correction by dataset
    xyCorr , xyCorrFile = '' , ''
    for datasetKey,tag in xyCorrsByDataset.iteritems():
      if re.match(re.compile(datasetKey),secondaryDatasetName):
        xyCorr = tag
        xyCOrrFile = 'multPhiCorr_ReMiniAOD_Data_'+xyCorr.split('_')[2]+'_80X_sumPt_cfi'
    #Put xy correction into config
    config_txt.replace('#MetPhiCorrectionsInsertHere','from MetTools.MetPhiCorrections.tools.'+xyCorrFile+' import '+xyCorr+' as multPhiCorrParams_Txy_25ns')

    # substitute the output filename at the end
    config_txt += '\nprocess.TFileService.fileName = "'+outputFile+'.root"\n'
    # substitute the global tag name at the end if needed, and feed it into rootTupleEvent
    if globalTag != '':
      config_txt += '\nprocess.GlobalTag.globaltag = "'+globalTag+'"\n'
      config_txt += '\nprocess.rootTupleEvent.globalTag = "'+globalTag+'"\n'
    with open(newCmsswConfig,'w') as cfgNew_file:
      cfgNew_file.write(config_txt)

    # now make the rest of the crab3 config
    if isData:
      config.Data.splitting = 'LumiBased' #LumiBased for data
      if math.fabs(nUnitsPerJob)==1:
        print 'WARNING: You specified +/-1 lumis per job; using default lumis per job of 100 instead'
        config.Data.unitsPerJob = 40
    config.Data.unitsPerJob = nUnitsPerJob
    print 'INFO: using',nUnitsPerJob,'units (files/lumis) per job'
    config.General.requestName = datasetName
    config.JobType.psetName = newCmsswConfig
    config.Data.totalUnits = nUnits
    if options.jsonFile is not None:
      if options.prevJsonFile is not None:
        print 'Using the subtraction between previous json and new json; WARNING: if lumis changed from good in previous to bad in new json, this will not remove them'
        from WMCore.DataStructs.LumiList import LumiList
        prevJsonLumiList = LumiList(url=options.prevJsonFile) if 'http:' in options.prevJsonFile else LumiList(filename=options.prevJsonFile)
        currentJsonLumiList = LumiList(url=options.jsonFile) if 'http:' in options.jsonFile else LumiList(filename=options.jsonFile)
        newLumiList = currentJsonLumiList - prevJsonLumiList
        newLumiList.writeJSON('newJSON_minus_oldJSON.json')
        config.Data.lumiMask = 'newJSON_minus_oldJSON.json'
      else:
        config.Data.lumiMask = options.jsonFile
    if options.runRange is not None:
      config.Data.runRange = runRange
    # and submit
    print 'submit!'
    #crabSubmit(config)
    # workaround for cmssw multiple-loading problem
    # submit in subprocess
    q = Queue()
    p = Process(target=crabSubmit, args=(config,))
    p.start()
    p.join()
    if q.get()==-1:
      exit(-1)
    

print 'Done!' 
exit(0)
