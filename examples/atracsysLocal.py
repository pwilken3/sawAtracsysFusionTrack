import os
import platform
import sys
import time

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np

import cisstCommonPython as cmn
import cisstVectorPython as vct
import cisstOSAbstractionPython as osa
import cisstMultiTaskPython as mts
import cisstParameterTypesPython as prm

from Frame import *

name = 'My Tracker'
#period = 0.01

cmn.cmnLogger_SetMask(cmn.CMN_LOG_ALLOW_ALL)
cmn.cmnLogger_SetMaskFunction(cmn.CMN_LOG_ALLOW_ALL)
cmn.cmnLogger_SetMaskDefaultLog(cmn.CMN_LOG_ALLOW_ALL)
cmn.cmnLogger_SetMaskClassMatching('mts', cmn.CMN_LOG_ALLOW_ALL)

# cmn.cmnLogger_SetMask(cmn.CMN_LOG_ALLOW_ERRORS_AND_WARNINGS)
# cmn.cmnLogger_SetMaskFunction(cmn.CMN_LOG_ALLOW_ERRORS_AND_WARNINGS)
# cmn.cmnLogger_SetMaskDefaultLog(cmn.CMN_LOG_ALLOW_ERRORS_AND_WARNINGS)
# cmn.cmnLogger_SetMaskClassMatching('mts', cmn.CMN_LOG_ALLOW_ERRORS_AND_WARNINGS)

#Note - repid communication with the device may cause comm errors.

#load the NDI config file
pathToConfig = '/home/rems/dev/rems/data/config/'

configuration = os.path.join(pathToConfig, 'configAtracsysFusionTrack.json')

print 'Connecting to GCM from python'
manager = mts.mtsManagerLocal.GetInstance('localhost', 'pythonProc')
#the above will crash if GCM is not available.

manager = mts.mtsManagerLocal.GetInstance()
manager.CreateAllAndWait(5.0)
manager.StartAllAndWait(5.0)

proxy = mts.mtsComponentWithManagement('{}Proxy'.format(name))
manager.AddComponent(proxy)
proxy.CreateAndWait(5.0)
time.sleep(0.5)

services = proxy.GetManagerComponentServices()

#create an instance of the tracker
result = services.Load('sawAtracsysFusionTrack')
assert result, 'Failed to load {} using component services'.format('sawAtracsysFusionTrack')

args = mts.mtsTaskContinuousConstructorArg(name)
result = services.ComponentCreate('mtsAtracsysFusionTrack', args)
assert result, 'Failed to create {} of type {}'.format(name, 'mtsAtracsysFusionTrack')

component = manager.GetComponent(name)
component.Configure(configuration)


component.CreateAndWait(5.0)
component.StartAndWait(5.0)

time.sleep(4.5)

print("Test 0")

#create the main interface to the tracker
controller = proxy.AddInterfaceRequiredAndConnect((name, 'Controller'))

print("Test 1")

#initialize controller
#controller.PortHandlesInitialize()
#controller.PortHandlesQuery()
#controller.PortHandlesEnable()

print("Test 2")

# create an interface for the tracked pointer body
armBodyName = 'Arm Tool'
armBody = proxy.AddInterfaceRequiredAndConnect((name, armBodyName))

# create an interface for the tracked pointer body
referenceBodyName = 'Reference'
referenceBody = proxy.AddInterfaceRequiredAndConnect((name, referenceBodyName))

# create an interface for the tracked pointer body
pointerBodyName = 'Tip Tool'
pointerBody = proxy.AddInterfaceRequiredAndConnect((name, pointerBodyName))

print("Test 3")

def GetPose():
	f = Frame()
	pose = pointerBody.GetPositionCartesian()
	if pose.GetValid():  # if visible
		f.FromVctFrm3(pose.Position())
		f.IsValid = True
	#else return just the identity
	return f
#pointer 
def GetTranslation():
	pose = pointerBody.GetPositionCartesian()
	if pose.GetValid():  # if visible
		return np.copy(pose.Position().Translation())
	else:
		return np.zeros(3)

def GetPoseInRef():
	r = GetReference()
	f = Frame()
	pointerInRef = Frame()
	pose = pointerBody.GetPositionCartesian()
	if pose.GetValid():  # if visible
		f.FromVctFrm3(pose.Position())
		pointerInRef = r.Inverse() * f;
		pointerInRef.IsValid = r.IsValid
		#will return global pointer pose.
		if (not r.IsValid):
			print 'Reference not valid'
	elif (not r.IsValid):
		print 'Reference and pointer not valid'
	else: 
		print 'Pointer not valid'
	#else return just the identity
	return pointerInRef

def GetTranslationInRef():
	f = GetPoseInRef()
	return f.Translation()

def GetReference():
	f = Frame()
	pose = referenceBody.GetPositionCartesian()
	if pose.GetValid():  # if visible
		f.FromVctFrm3(pose.Position())
		f.IsValid = True
	#else return just the identity
	return f

def GetPointerPosFiltered(numSamples = 10):
    # returns identity () if there are obstructions
    sleepTime = 0.1;

    points = []
    for i in numSamples:
        frame = GetPose()
        if (frame.IsValid):
            points.append(frame.Translation())
        else:
            print "failed to get valid tracker frame."
        time.sleep(sleepTime)

    if (np.shape(points)[0] > 0):
        return np.mean(points, axis=0)
    else:
        print 'Could not get reference data'
        return np.zeros(3)

def PrintTranslation():
	print GetTranslation()

def PrintTranslationInRef():
	print GetTranslationInRef()

def PrintPointerTranslationCont():
	while True:
		time.sleep(0.5)
		PrintTranslation()

def PrintPointerInRefTranslationCont():
	while True:
		time.sleep(0.5)
		PrintTranslationInRef()

def PrintPointerAndRefTranslationCont():
	while True:
		time.sleep(1)
		print "P   :", GetTranslation()
		print "R   :", GetReference().Translation()
		print "PinR:", GetPoseInRef().Translation()

def PlotSamplePoints():
	numPoints = 100;
	xv = numpy.zeros(numPoints)
	yv = numpy.zeros(numPoints) 
	zv = numpy.zeros(numPoints)

	for i in range(0,numPoints):
		time.sleep(0.05) #the updated rate is slow... maybe 30 fps.
		pose = pointerBody.GetPositionCartesian()
		if pose.GetValid():  # if visible
			xv[i] = pose.Position().Translation()[0]
			yv[i] = pose.Position().Translation()[1]
			zv[i] = pose.Position().Translation()[2]
		else: 
			print 'Point ' + str(i) + 'is not visible'

	fig = plt.figure()
	ax = fig.add_subplot(111, projection='3d')

	#x =[1,2,3,4,5,6,7,8,9,10]
	#y =[5,6,2,3,13,4,1,2,4,8]
	#z =[2,3,3,3,5,7,9,11,9,10]

	ax.scatter(xv, yv, zv, c='r', marker='o')

	ax.set_xlabel('X Label')
	ax.set_ylabel('Y Label')
	ax.set_zlabel('Z Label')

	plt.show()

def GetAllPoses():
    trTool = Frame()
    trTool.FromVctFrm3(pointerBody.GetPositionCartesian().Position())
    trArm = Frame()
    trArm.FromVctFrm3(armBody.GetPositionCartesian().Position())
    trBase = Frame()
    trBase.FromVctFrm3(referenceBody.GetPositionCartesian().Position())
    return trTool, trArm, trBase
