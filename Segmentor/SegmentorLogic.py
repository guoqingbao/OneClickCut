# Project - One Click Cut  - "To segment 3D ROI, like tumor, leison from given 3D volume"
# Author: Guoqing Bao
# Supervisor: Sidong Liu; Weidong Cai; 
# The University of Sydney
# 2017-05-08
#---------------------------------------------------------------------------
# The actual implementation 3D segmentation of extension OneClickCut
# the main segmentation logic is implemented in "run" function,
# the UI model will call the run fucntion after user marked the inital seeds
# region-grow(grow-cut) algorithm was first used, then Opencv was used for refinement of 
# the output of grow-cut, then the 3D model was presented in 3D view
#---------------------------------------------------------------------------

import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy as v2n
from SegmentorUtils import SegmentorUtils

#---------------------------------------------------------------------------
#Dynamically load Opencv library before import Opencv, since other PC may not have this library installed
print 'Current One-Click-Cut path = '
scriptPath = os.path.dirname(os.path.abspath(__file__))
print scriptPath
# load the python wrapped OpenCV module
try:
    print 'Trying to import cv2'
    # the module is in the python path
    import cv2
    print 'Imported!'
except ImportError:
    print 'Trying to import from file'
    # for the build directory, load from the file
    import imp, platform

    cv2File = 'cv2.pyd'
    print 'Loading cv2 from ',cv2File
    cv2 = imp.load_dynamic('cv2', cv2File)
    print 'Imported from File!'
#---------------------------------------------------------------------------

#
# SegmentorLogic, the main segmentation logic is implemented in "run" function,
# the UI model will call the run fucntion after user marked the inital seeds
#

class SegmentorLogic(ScriptedLoadableModuleLogic):
  
  #
  #returns true if the passed in volume node has valid image data
  #
  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True


  #
  #Validates if the output is not the same as input
  #
  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True


  #
  #used in refinement stage, used for find the biggest contour in a binary image
  #
  def findBiggestContour(self,image):
    
    _, contours, hierarchy = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contour_size = [(cv2.contourArea(contour), contour) for contour in contours]
    biggest_contour = max(contour_size, key=lambda x:x[0])[1]
    
    #mask = np.zeros(image.shape, np.uint8)
    #cv2.drawContours(mask, [biggest_contour], -1, 255, -1)
    return biggest_contour, contours

  #
  #take screen shot, implemented by template of 3D slicer
  #
  def takeScreenshot(self,name,description,type=-1):
    # show the message even if not taking a screen shot
    slicer.util.delayDisplay('Take screenshot: '+description+'.\nResult is available in the Annotations module.', 3000)

    lm = slicer.app.layoutManager()
    # switch on the type to get the requested window
    widget = 0
    if type == slicer.qMRMLScreenShotDialog.FullLayout:
      # full layout
      widget = lm.viewport()
    elif type == slicer.qMRMLScreenShotDialog.ThreeD:
      # just the 3D window
      widget = lm.threeDWidget(0).threeDView()
    elif type == slicer.qMRMLScreenShotDialog.Red:
      # red slice window
      widget = lm.sliceWidget("Red")
    elif type == slicer.qMRMLScreenShotDialog.Yellow:
      # yellow slice window
      widget = lm.sliceWidget("Yellow")
    elif type == slicer.qMRMLScreenShotDialog.Green:
      # green slice window
      widget = lm.sliceWidget("Green")
    else:
      # default to using the full window
      widget = slicer.util.mainWindow()
      # reset the type so that the node is set correctly
      type = slicer.qMRMLScreenShotDialog.FullLayout

    # grab and convert to vtk image data
    qpixMap = qt.QPixmap().grabWidget(widget)
    qimage = qpixMap.toImage()
    imageData = vtk.vtkImageData()
    slicer.qMRMLUtils().qImageToVtkImageData(qimage,imageData)

    annotationLogic = slicer.modules.annotations.logic()
    annotationLogic.CreateSnapShot(name, description, type, 1, imageData)

  #
  #fucntion for rotate the image, used in refinement stage
  #
  def rotateImage(self,image, angle):
      image_center = tuple(np.array(image.shape)/2)
      rot_mat = cv2.getRotationMatrix2D(image_center,angle,1.0)
      result = cv2.warpAffine(image, rot_mat, image.shape,flags=cv2.INTER_LINEAR)
      return result


  #
  #Region growing algorithm in 3D space, modified from grow-cut in 3D slicer
  #However, the result of this grow-cut algorithm is rough, need further refinement
  #
  def growCut(self, inputVolumeData, seedingROIData, outputROIData, compensateIntensity):

    # Get the mean of the seeding ROI
    seedingROI_coords   = np.where(seedingROIData > 0)
    seedingROI_values   = inputVolumeData[seedingROI_coords]
    
    # # the location of the seeding voxel
    sx = seedingROI_coords[0][seedingROI_values.argmax()]
    sy = seedingROI_coords[1][seedingROI_values.argmax()]
    sz = seedingROI_coords[2][seedingROI_values.argmax()]

    # compensateIntensity is used to select the voxels within a range  
    ROI_min = seedingROI_values.min() - compensateIntensity
    ROI_max = seedingROI_values.max() + compensateIntensity

    # Dimension of the input volume 
    dx, dy, dz = inputVolumeData.shape
    print "inputVolumeData shape", dx, dy, dz

    iteration = 0
    # the local searching radius
    radius = 1
    segutil = SegmentorUtils()
    while True:
        
        iteration = iteration + 1 
        # First stop criterion: reach the boundary of the image
        searching_extend    = np.array([iteration+radius-sx, sx+iteration+radius+1-dx, \
                                         iteration+radius-sy, sy+iteration+radius+1-dy, \
                                         iteration+radius-sz, sz+iteration+radius+1-dz])
        if (searching_extend >= 0).any(): 
            break

        # Second stop criterion: there is no new voxel with in the global value range 
        new_voxel_coords    = segutil.find_new_voxels(sx, sy, sz, iteration)
        new_voxel_values    = inputVolumeData[new_voxel_coords[:, 0], new_voxel_coords[:, 1], new_voxel_coords[:, 2]]
        glb_voxel_indices   = np.where(np.logical_and(new_voxel_values < ROI_max, new_voxel_values > ROI_min))        
        
        if not glb_voxel_indices: 
            break
        
        else:
            for i in glb_voxel_indices[0]:
                lx, ly, lz          = new_voxel_coords[i, :] 
                patch_boolen        = outputROIData[lx - 1 : lx + 2, ly - 1 : ly + 2, lz - 1 : lz + 2]   

                if patch_boolen.sum() > 1:
                    local_value     = inputVolumeData[lx, ly, lz] 
                    patch_values    = inputVolumeData[lx - 1 : lx + 2, ly - 1 : ly + 2, lz - 1 : lz + 2] 
                    if patch_boolen.shape != patch_values.shape:
                      break
                    boolen_values   = patch_values[:] * patch_boolen[:]
                    
                    existing_values = boolen_values[np.where(boolen_values > 0)]
                    local_min       = existing_values.min() - compensateIntensity
                    local_max       = existing_values.max() + compensateIntensity                 
                    # Third stop criterion: the voxel value is beyond the range of local existing neighbors
                    if local_value < local_max and local_value > local_min:
                        outputROIData[lx, ly, lz] = 1

    pass

  #This function modified from "Model Maker" in 3D slicer
  # create a model using the command line module
  # based on the current editor parameters
  #
  def makeModel(self,volumeNode, labelNumber, smoothValue):
    #the volume need to present must valid
    if not volumeNode:
      return


    # set up the model maker node
    parameters = {}
    parameters['Name'] = "EditorModel"
    parameters["InputVolume"] = volumeNode.GetID()
    parameters['FilterType'] = "Sinc"

    # build only the currently selected model.
    parameters['Labels'] = labelNumber #using default label, that can further improved by using label that user selected
    parameters["StartLabel"] = -1
    parameters["EndLabel"] = -1

    parameters['GenerateAll'] = False
    parameters["JointSmoothing"] = False
    parameters["SplitNormals"] = True
    parameters["PointNormals"] = True
    parameters["SkipUnNamed"] = True
    parameters["Decimate"] = 0.25
    parameters["Smooth"] = smoothValue #defaul smooth parameter

    #
    # output
    # - make a new hierarchy node if needed
    #
    numNodes = slicer.mrmlScene.GetNumberOfNodesByClass( "vtkMRMLModelHierarchyNode" )
    outHierarchy = None
    for n in xrange(numNodes):
      node = slicer.mrmlScene.GetNthNodeByClass( n, "vtkMRMLModelHierarchyNode" )
      if node.GetName() == "Editor Models":
        outHierarchy = node
        break

    if not outHierarchy:
      outHierarchy = slicer.vtkMRMLModelHierarchyNode()
      outHierarchy.SetScene( slicer.mrmlScene )
      outHierarchy.SetName( "Editor Models" )
      slicer.mrmlScene.AddNode( outHierarchy )

    parameters["ModelSceneFile"] = outHierarchy

    modelMaker = slicer.modules.modelmaker

    #
    # run the task (in the background)
    # - use the GUI to provide progress feedback
    # - use the GUI's Logic to invoke the task
    # - model will show up when the processing is finished
    #
    slicer.cli.run(modelMaker, None, parameters)

    
    pass


  #
  #The actual segmentation algorithms implemented in this function
  #firstly, use grow cut to make initla ROI
  #then, use opencv(convex hull, morphological operation) to refine the ROI
  #fianlly, present the ROI model in 3D view
  #
  def run(self, inputVolume,seedingROI, paintSize, automodel, compensateIntensity, labelNumber, smoothValue):

    if not self.isValidInputOutputData(inputVolume, seedingROI):
       slicer.util.errorDisplay('Please select a input volume first!')
       return False

    slicer.util.showStatusMessage( "Segmentation Started...", 500 )
    # Read in the input volume
    inputVolumeData = slicer.util.array(inputVolume.GetID())
    
    # Read in the seeding ROI, the initial label marked by user
    seedingROIData  = slicer.util.array(seedingROI.GetID())
    
    # Copy seeding node, create a new volume node as the result of region grow
    outputROI_name  = seedingROI.GetName() + '_grow'
    seedingOutputROI       = slicer.modules.volumes.logic().CloneVolume(slicer.mrmlScene, seedingROI, outputROI_name)
    outputROIData   = slicer.util.array(seedingOutputROI.GetID())
    
    #create output node
    outputVolume_name = inputVolume.GetName() + '_processed'
    volumesLogic = slicer.modules.volumes.logic()
    outputVolume = volumesLogic.CloneVolume(slicer.mrmlScene, inputVolume, outputVolume_name)
    outputVolumeData = slicer.util.array(outputVolume.GetID())


    # Dimension of the input volume 
    dx, dy, dz = inputVolumeData.shape
    print "Start Performe Grow-Cut: inputVolumeData shape", dx, dy, dz

    #start grow cut algorithm, 
    #that will use initial label and region grow to generate ROI ##########
    self.growCut(inputVolumeData,seedingROIData,outputROIData, compensateIntensity)
    
    dx, dy, dz = outputROIData.shape
    print "Start to Find ROI Convexhull: outputROIData shape", dx, dy, dz
    

    #Start to optimize the result of grow-cut############
    #since the result of grow-cut need postproceesing
    #use the opencv to find convex hull of each slice (generated by grow cuts)
    #then draw the convex hull and do morphological operation to optimize the results
    for i in range(dx):
      #each of the slice
      oneslice = outputROIData[i:i+1, 0:dy,0:dz][0]

      mul_array = np.full((dy,dz),255,np.float32);
      #convert each slice to the format that Opencv can process, range from 0-1 to 0-255
      oneslice = oneslice * mul_array
      
      #if the slice have label info(region grow algorithm is grown to this slice)
      if oneslice.max()>0:
        #convert to image that Opencv can process
        img = cv2.convertScaleAbs(oneslice)

        #a binary threshold to change the slice to binary, that will enable us to further postprocessing
        ret, img = cv2.threshold(oneslice, 1, 255,cv2.THRESH_BINARY)

        #find the label areas
        points = np.argwhere(img==255)
        #using the label areas(contains many pixels) to generate a convex hull
        ##(the minimized region that can contain label areas)
        poly = cv2.convexHull(points)
        img[img>=0] = 0
        contours = []
        contours.append(poly)

        #use the convex hull as new label area
        cv2.drawContours(img,contours, -1, (255,255,255), -1)

        #rotate the image to match the original dimension
        img = self.rotateImage(img,90)
        img = img[::-1,:]

        #morphological operation to smooth the label area
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5))
        img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)

        #convert the new label image to original format
        oneslice = img / mul_array
        outputROIData[i:i+1, 0:dy,0:dz][0] = oneslice

    valid_output_values = np.where(outputROIData>0);
    outputVolumeData[outputROIData>0] = 100
    #outputVolumeData[outputROIData>0] = inputVolumeData[valid_output_values]

    outputVolume.GetImageData().Modified()
    seedingOutputROI.GetImageData().Modified()
    
    # make the output volume appear in all the slice views
    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
    selectionNode.SetReferenceActiveLabelVolumeID(seedingOutputROI.GetID())
    slicer.app.applicationLogic().PropagateVolumeSelection(0)

    
    #Segmentation Complete, Start to Present 3D Result##########
    if automodel:
      self.makeModel(seedingOutputROI, labelNumber, smoothValue)
    slicer.util.showStatusMessage( "Segmentation Complete, 3D Result Presented!", 2000 )

    return True
#---------------------------------------------------------------------------
