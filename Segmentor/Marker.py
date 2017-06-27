# Project - OneClickCut - "To segment 3D ROI, like tumor, leison from given 3D volume"
# Author: Guoqing Bao
# Supervisor: Sidong Liu; Weidong Cai; 
# The University of Sydney
# 2017-05-08
#---------------------------------------------------------------------------
# Implement simple paint effect.
# This class used for marking the seeds, modified from the Editor module of 3D Slicer
# UI module will call the listen function of this class, after listening the mouse event,
# this calss will process the user input event, handle the marking seeds function
#---------------------------------------------------------------------------
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy as v2n
from slicer.util import VTKObservationMixin

#---------------------------------------------------------------------------
#Marker class used for marking seeds
class Marker:
  def setup(self, parent, radius, which):
    #firstly, find the proper instance for following marking
    self.sliceWidget = slicer.app.layoutManager().sliceWidget(which)
    self.sliceLogic = self.sliceWidget.sliceLogic()
    self.sliceView = self.sliceWidget.sliceView()
    #interactor is very important for processing user input events, such as mouse move
    self.interactor = self.sliceView.interactorStyle().GetInteractor()
    self.renderWindow = self.sliceWidget.sliceView().renderWindow()
    self.renderer = self.renderWindow.GetRenderers().GetItemAsObject(0)
    self.parent = parent

    #actors used for paint effects, the paint effects just like 3D Slicer's paint effect
    self.actors = []
    # the current operation
    self.actionState = None

    # configuration variables
    self.delayedPaint = True #delayed paint by default, that will show paint effects when marking the seeds
    self.radius = radius #default marking size

    # interaction state variables
    self.position = [0, 0, 0]
    self.paintCoordinates = []
    self.feedbackActors = []
    self.lastRadius = 0

    # scratch variables
    self.rasToXY = vtk.vtkMatrix4x4()

    # initialization of painter
    self.brush = vtk.vtkPolyData()
    self.createGlyph(self.brush)
    #self.createGlyph(self.brush)
    self.mapper = vtk.vtkPolyDataMapper2D()
    self.actor = vtk.vtkActor2D()
    self.mapper.SetInputData(self.brush)
    self.actor.SetMapper(self.mapper)

    self.savedCursor = None

    #used for remember events, that will make it eaiser to remove events from listener
    self.interactorObserverTags  = []

  def resetActor(self):
    #actors used for paint effects, the paint effects just like 3D Slicer's paint effect
    self.renderer.RemoveActor2D(self.actor)
    self.actors = []
    # the current operation
    self.actionState = None

    # interaction state variables
    self.position = [0, 0, 0]
    self.paintCoordinates = []
    self.feedbackActors = []
    self.lastRadius = 0

    # scratch variables
    self.rasToXY = vtk.vtkMatrix4x4()

    # initialization of painter
    self.brush = vtk.vtkPolyData()
    self.createGlyph(self.brush)
    #self.createGlyph(self.brush)
    self.mapper = vtk.vtkPolyDataMapper2D()
    self.actor = vtk.vtkActor2D()
    self.mapper.SetInputData(self.brush)
    self.actor.SetMapper(self.mapper)

    self.savedCursor = None
    self.renderer.AddActor2D(self.actor)
    self.actors.append(self.actor)
  pass
  #
  #Create a poly graph, used for marking the seeds, 
  #mark a poly graph after user click instead of just mark single pixel
  #
  def createGlyph(self, polyData):
    sliceNode = self.sliceWidget.sliceLogic().GetSliceNode()
    self.rasToXY.DeepCopy(sliceNode.GetXYToRAS())
    self.rasToXY.Invert()
    maximum, maxIndex = 0,0
    for index in range(3):
      if abs(self.rasToXY.GetElement(0, index)) > maximum:
        maximum = abs(self.rasToXY.GetElement(0, index))
        maxIndex = index
    point = [0, 0, 0, 0]
    point[maxIndex] = self.radius
    xyRadius = self.rasToXY.MultiplyPoint(point)
    import math
    xyRadius = math.sqrt( xyRadius[0]**2 + xyRadius[1]**2 + xyRadius[2]**2 )


    # make a circle paint brush
    points = vtk.vtkPoints()
    lines = vtk.vtkCellArray()
    polyData.SetPoints(points)
    polyData.SetLines(lines)
    PI = 3.1415926
    TWOPI = PI * 2
    PIoverSIXTEEN = PI / 16
    prevPoint = -1
    firstPoint = -1
    angle = 0
    while angle <= TWOPI:
      x = xyRadius * math.cos(angle)
      y = xyRadius * math.sin(angle)
      p = points.InsertNextPoint( x, y, 0 )
      if prevPoint != -1:
        idList = vtk.vtkIdList()
        idList.InsertNextId(prevPoint)
        idList.InsertNextId(p)
        polyData.InsertNextCell( vtk.VTK_LINE, idList )
      prevPoint = p
      if firstPoint == -1:
        firstPoint = p
      angle = angle + PIoverSIXTEEN

    # make the last line in the circle
    idList = vtk.vtkIdList()
    idList.InsertNextId(p)
    idList.InsertNextId(firstPoint)
    polyData.InsertNextCell( vtk.VTK_LINE, idList )
 
  #
  #Listen the user event, such as mouse event
  #processEvent function will handle these events
  def listen(self):
    if len(self.interactorObserverTags) >0:
        return
    #   event processors
    events = ( vtk.vtkCommand.LeftButtonPressEvent,
      vtk.vtkCommand.LeftButtonReleaseEvent,
      vtk.vtkCommand.MiddleButtonPressEvent,
      vtk.vtkCommand.MiddleButtonReleaseEvent,
      vtk.vtkCommand.RightButtonPressEvent,
      vtk.vtkCommand.RightButtonReleaseEvent,
      vtk.vtkCommand.MouseMoveEvent,
      vtk.vtkCommand.KeyPressEvent,
      vtk.vtkCommand.EnterEvent,
      vtk.vtkCommand.LeaveEvent
      )
    
    for e in events:
      tag = self.interactor.AddObserver(e, self.processEvent, 1.0)
      self.interactorObserverTags.append(tag)
      #print "AddObserver", tag

    self.actor.VisibilityOff()
    self.rasToXY = vtk.vtkMatrix4x4()
    self.renderer.AddActor2D(self.actor)
    self.actors.append(self.actor)
  #
  #Set the marker size
  #
  def setMarkerSize(self, r):
    self.radius = r
    print "setMarkerSize", r
	
  #
  #Call this function when painting, if delayed painting, show the paint effects
  #otherwise do direct painting
  #
  def paintAddPoint(self, x, y):
    self.paintCoordinates.append( (x, y) )
    if self.delayedPaint:
      self.paintFeedback()
    else:
      self.paintApply()
  pass

  #
  #Hide the cursor when painting
  #
  def cursorOff(self):
    self.savedCursor = self.sliceWidget.cursor
    qt_BlankCursor = 10
    self.sliceWidget.setCursor(qt.QCursor(qt_BlankCursor))


  #
  #Show the cursor after paint the label
  #
  def cursorOn(self):
    if self.savedCursor:
      self.sliceWidget.setCursor(self.savedCursor)
    else:
      self.sliceWidget.unsetCursor()


  #
  #Show the paint effects
  #
  def paintFeedback(self):
    if self.paintCoordinates == []:
      for a in self.feedbackActors:
        self.renderer.RemoveActor2D(a)
      self.feedbackActors = []
      return

    for xy in self.paintCoordinates[len(self.feedbackActors):]:
      a = vtk.vtkActor2D()
      self.feedbackActors.append(a)
      a.SetMapper(self.mapper)
      a.SetPosition(xy[0], xy[1])
      property = a.GetProperty()
      property.SetColor(.7, .7, 0)
      property.SetOpacity( .5 )
      self.renderer.AddActor2D( a )
  pass


  #
  #Don't pass the event to 3D slicer
  #
  def abortEvent(self,event):
    for tag in self.interactorObserverTags:
      cmd = self.interactor.GetCommand(tag)
      cmd.SetAbortFlag(1)

  #
  #Process the marking event, after listen to the 3D volume,
  #the mouse button down, mouse move and release event will let us paint the label(marking seeds)
  #
  def processEvent(self, caller=None, event=None):
    """
    handle events from the render window interactor
    """
    if not self.parent.enableEvent():
        return
    #if super(SegmentorWidget,self).processEvent(caller,event):
    #  return

    # interactor events, user mouse button down, start paint
    if event == "LeftButtonPressEvent":
      self.actionState = "painting"
      #don't show the cursor when painting
      self.cursorOff()
      print "start painting"
      xy = self.interactor.GetEventPosition()
      #since we use delayed paint, this will make a paint effect instead of real paint,
      #the real paint happens after user released the mouse button
      self.paintAddPoint(xy[0], xy[1])

      #don't pass this event to the 3D slicer, 
      #since we don't want the 3D slicer use this event do other things when painting
      self.abortEvent(event)

    #user mouse released, do real paint
    elif event == "LeftButtonReleaseEvent":
      self.paintApply()
      self.actionState = None
      #show the curson after paint
      self.cursorOn()
      print "end painting"
      self.parent.onEndPaint()

    #when we are in "painting" state, mouse move will let us paint the label when mouse move
    elif event == "MouseMoveEvent":
      self.actor.VisibilityOn()
      if self.actionState == "painting":
        xy = self.interactor.GetEventPosition()
        self.paintAddPoint(xy[0], xy[1])
        self.abortEvent(event)
    elif event == "EnterEvent" or event=="RightButtonReleaseEvent":
      self.resetActor()
      self.actor.VisibilityOn()
      print "resetActor"
    elif event == "LeaveEvent":
      self.actor.VisibilityOff()
      print "LeaveEvent"

    else:   
        return

    # events from the slice node
    #if caller and caller.IsA('vtkMRMLSliceNode'):
    #  if hasattr(self,'brush'):
    #    self.createGlyph(self.brush)

    self.positionActors()
    pass

  #
  #This funtion will add paint effect on label node
  #
  def positionActors(self):
    if hasattr(self,'actor'):
      self.actor.SetPosition( self.interactor.GetEventPosition() )
      self.sliceView.scheduleRender()

  #
  #Notify the 3D slicer that label node(or other nodes) was changed
  #
  def markVolumeNodeAsModified(self,volumeNode):
    if volumeNode.GetImageDataConnection():
      volumeNode.GetImageDataConnection().GetProducer().Update()
    if volumeNode.GetImageData().GetPointData().GetScalars() is not None:
      volumeNode.GetImageData().GetPointData().GetScalars().Modified()
    volumeNode.GetImageData().Modified()
    volumeNode.Modified()


  #
  #Do the real paint work, will first get label node, 
  #then call paintBrush do real paint, then show paint effects
  #
  def paintApply(self):
    labelNode = self.parent.onPaintBefore()
    for xy in self.paintCoordinates:
        self.paintBrush(labelNode, xy[0], xy[1])
    self.paintCoordinates = []
    self.paintFeedback()
    #it is import to notify the 3D slicer that we changed the label node
    if labelNode:
      self.markVolumeNodeAsModified(labelNode)

  pass


  #
  #This function will do real paint, use a brush to paint the seeds instead of draw single pixel
  #Paint label is 1 by default
  #
  def paintBrush(self,labelNode, x, y):
    if not labelNode:
      # if there's no label, we can't paint
      return
    sliceLogic = self.sliceWidget.sliceLogic()
    sliceNode = sliceLogic.GetSliceNode()
    labelLogic = sliceLogic.GetLabelLayer()
    #labelNode = self.seedingSelector.currentNode()
    labelImage = labelNode.GetImageData()
    backgroundLogic = sliceLogic.GetBackgroundLayer()
    backgroundNode = backgroundLogic.GetVolumeNode()
    backgroundImage = backgroundNode.GetImageData()
    #
    # get the brush bounding box in ijk coordinates
    # - get the xy bounds
    # - transform to ijk
    # - clamp the bounds to the dimensions of the label image
    #
    bounds = self.brush.GetPoints().GetBounds()
    left = x + bounds[0]
    right = x + bounds[1]
    bottom = y + bounds[2]
    top = y + bounds[3]

    xyToIJK = labelLogic.GetXYToIJKTransform()
    tlIJK = xyToIJK.TransformDoublePoint( (left, top, 0) )
    trIJK = xyToIJK.TransformDoublePoint( (right, top, 0) )
    blIJK = xyToIJK.TransformDoublePoint( (left, bottom, 0) )
    brIJK = xyToIJK.TransformDoublePoint( (right, bottom, 0) )

    dims = labelImage.GetDimensions()

    # clamp the top, bottom, left, right to the
    # valid dimensions of the label image
    tl = [0,0,0]
    tr = [0,0,0]
    bl = [0,0,0]
    br = [0,0,0]
    for i in xrange(3):
      tl[i] = int(round(tlIJK[i]))
      if tl[i] < 0:
        tl[i] = 0
      if tl[i] >= dims[i]:
        tl[i] = dims[i] - 1
      tr[i] = int(round(trIJK[i]))
      if tr[i] < 0:
        tr[i] = 0
      if tr[i] >= dims[i]:
        tr[i] = dims[i] - 1
      bl[i] = int(round(blIJK[i]))
      if bl[i] < 0:
        bl[i] = 0
      if bl[i] >= dims[i]:
        bl[i] = dims[i] - 1
      br[i] = int(round(brIJK[i]))
      if br[i] < 0:
        br[i] = 0
      if br[i] >= dims[i]:
        br[i] = dims[i] - 1

    # If the region is smaller than a pixel then paint it using paintPixel mode,
    # to make sure at least one pixel is filled on each click
    maxRowDelta = 0
    maxColumnDelta = 0
    for i in xrange(3):
      d = abs(tr[i] - tl[i])
      if d > maxColumnDelta:
        maxColumnDelta = d
      d = abs(br[i] - bl[i])
      if d > maxColumnDelta:
        maxColumnDelta = d
      d = abs(bl[i] - tl[i])
      if d > maxRowDelta:
        maxRowDelta = d
      d = abs(br[i] - tr[i])
      if d > maxRowDelta:
        maxRowDelta = d
    if maxRowDelta<=1 or maxColumnDelta<=1 :
      #self.paintPixel(x,y)
      return

    #
    # get the layers and nodes
    # and ijk to ras matrices including transforms
    #
    backgroundIJKToRAS = vtk.vtkMatrix4x4()
    labelIJKToRAS = vtk.vtkMatrix4x4()
    backgroundNode.GetIJKToRASMatrix(backgroundIJKToRAS)
    labelNode.GetIJKToRASMatrix(labelIJKToRAS)

    xyToRAS = sliceNode.GetXYToRAS()
    brushCenter = xyToRAS.MultiplyPoint( (x, y, 0, 1) )[:3]

    brushRadius = self.radius

    paintLabel = 1
    paintOver = True
    paintThreshold = False

    #
    # set up the painter class and let 'r rip!
    #
    if not hasattr(self,"painter"):
      self.painter = slicer.vtkImageSlicePaint()

    self.painter.SetBackgroundImage(backgroundImage)
    self.painter.SetBackgroundIJKToWorld(backgroundIJKToRAS)
    self.painter.SetWorkingImage(labelImage)
    self.painter.SetWorkingIJKToWorld(labelIJKToRAS)
    self.painter.SetTopLeft( tl[0], tl[1], tl[2] )
    self.painter.SetTopRight( tr[0], tr[1], tr[2] )
    self.painter.SetBottomLeft( bl[0], bl[1], bl[2] )
    self.painter.SetBottomRight( br[0], br[1], br[2] )
    self.painter.SetBrushCenter( brushCenter[0], brushCenter[1], brushCenter[2] )
    self.painter.SetBrushRadius( brushRadius )
    self.painter.SetPaintLabel(paintLabel)
    self.painter.SetPaintOver(paintOver)
    self.painter.SetThresholdPaint(paintThreshold)
    #self.painter.SetThresholdPaintRange(paintThresholdMin, paintThresholdMax)

    # paint the slice: same for circular and spherical brush modes
    self.painter.SetTopLeft( tl[0], tl[1], tl[2] )
    self.painter.SetTopRight( tr[0], tr[1], tr[2] )
    self.painter.SetBottomLeft( bl[0], bl[1], bl[2] )
    self.painter.SetBottomRight( br[0], br[1], br[2] )
    self.painter.SetBrushCenter( brushCenter[0], brushCenter[1], brushCenter[2] )
    self.painter.SetBrushRadius( brushRadius )
    self.painter.Paint()

  #
  #After user leave this extension or closed the scene, we drop the even listener, don't listen the mouse event
  #
  def dropListen(self):
    print "clean up actors and observers"
    #Remove the paint effects
    for a in self.actors:
      self.renderer.RemoveActor2D(a)
    self.sliceView.scheduleRender()
    #drop the event listener
    for tag in self.interactorObserverTags:
      self.interactor.RemoveObserver(tag)
      #print "RemoveObserver", tag
    self.interactorObserverTags = []

  #
  #For test paint effect
  #
  def testPaint(self,x,y):
      self.paintAddPoint(x,y)
  #
  #
  #
  def testApplyPaint(self):
      self.paintApply()
    