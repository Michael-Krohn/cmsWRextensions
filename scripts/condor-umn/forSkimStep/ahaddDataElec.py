import sys
import os
import subprocess
from shutil import copyfile

dataListDir = "/home/aevans/CMS/thesis/CMSSW_8_0_25/src/ExoAnalysis/cmsWRextensions/samples/data/"
dataList = dataListDir+"dataList_electron.txt"
jobsOutDir = "/data/whybee0b/user/aevans/"
outputNameSuffix = "data_skim_cfg_elec_"
hdfsStore = "/hdfs/cms/user/aevans/thesis/data_skim_cfg_elec/" 

with open(dataList) as f:
    lines = f.read().splitlines()

datas = []
xsecs = []
lineNum = 0
for line in lines:
    if lineNum < 2 : 
        lineNum+=1
        continue
    datas.append(line.split(':')[0].strip())
    xsecs.append(line.split(':')[1].strip())

#run over data
dataRootFiles = {}
for data in datas:
    #outputFolder = jobsOutDir+outputNameSuffix+data[:-4]+"/"
    outputFolder = jobsOutDir+"data_skim_cfg_elec/"
    storeFolder = hdfsStore+data[:-4]
    if not os.path.isdir(outputFolder) :
        print "data: "+data[:-4]+" not found at: "+outputFolder
        continue
    rootFiles = [""]
    fileNum = 0
    outputNum = 0
    for line in os.listdir(outputFolder):
        if (("-pool" not in line) and (".root" in line)):
            fileNum+=1
            if fileNum > 500:
                outputNum+=1
                fileNum = 0
                rootFiles.append("")
            rootFiles[-1]+=" "+outputFolder+line
    dataRootFiles[data] = rootFiles
    print len(dataRootFiles[data])
#ahadd together eventsWeight histogram
for data,files in dataRootFiles.items():
    outputNum = 0
    for rootFiles in files:
        print "defining output file"
        ahaddOut = hdfsStore+data[:-4]+"_eventsWeight_"+str(outputNum)+".root"
        subprocess.call ("rm "+ahaddOut, shell=True)
        print "old output file: "+ahaddOut+" deleted, hadding"
        ahaddCommand = "ahadd.py "+ahaddOut+" "+rootFiles
        subprocess.call(ahaddCommand, shell=True)
        outputNum+=1
