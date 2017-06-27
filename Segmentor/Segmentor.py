# Project - OneClickCut - "To segment 3D ROI, like tumor, leison from given 3D volume"
# Author: Guoqing Bao
# Supervisor: Sidong Liu; Weidong Cai; 
# The University of Sydney
# 2017-05-08
#---------------------------------------------------------------------------
# Segmentor Module, Include 2 Classes:
# "Segmentor" is the Scripted Loadable module, used for setting product info
# "SegmentorWidget" is the UI of this product, handle events(with the help of Marker class)
# SegmentorWidget have a member called "marker" which is the instance of Marker, used for selecting seeds
#---------------------------------------------------------------------------
import os
import vtk, qt, ctk, slicer
import logging
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from Marker import Marker
from SegmentorLogic import SegmentorLogic
#---------------------------------------------------------------------------

widgetForTest = None

#
# Segmentor Module
#

class Segmentor(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "OneClickCut Segmentation" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Segmentation"] # This extension was categorized into "Segmentation" 
    self.parent.dependencies = []
    self.parent.contributors = ["Guoqing Bao (The University of Sydney.)"] 

    #Display help information on the UI
    self.parent.helpText = """
    This extension implement the one-click-cut segmentation in 3D volume.
    After you load the volume,use the marker to mark the region you are interested, 
	this extension will automatically segment the ROI(include surrounding similar regions),
    then a 3D model of your ROI will automatically build.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Guoqing Bao, The University of Sydney.
    Please see 'help' to find how to use this extension.
    """ 




#---------------------------------------------------------------------------
#
# Segmentor Widget, The UI of this extension, derived from ScriptedLoadableModuleWidget and VTKObservationMixin
# VTKObservationMixin is used for handle events, like StartCloseEvent, StartImportEvent
#

class SegmentorWidget(ScriptedLoadableModuleWidget,VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """
  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    VTKObservationMixin.__init__(self)
    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # input volume selector, the input volume will automatically choose in Auto Mode
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene( slicer.mrmlScene )
    self.inputSelector.setToolTip( "Pick the input to the algorithm." )
    parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

    #
    # output volume selector, Auto create this node after segmentation complete, no need manually create
    #
    self.outputSelector = slicer.qMRMLNodeComboBox()
    self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.outputSelector.selectNodeUponCreation = True
    self.outputSelector.addEnabled = False
    self.outputSelector.removeEnabled = False
    self.outputSelector.noneEnabled = True
    self.outputSelector.showHidden = False
    self.outputSelector.showChildNodeTypes = False
    self.outputSelector.setMRMLScene( slicer.mrmlScene )
    self.outputSelector.setToolTip( "Output will automatically create after marking the ROI." )
    parametersFormLayout.addRow("Output Volume: ", self.outputSelector)
    #
    # Initial Seeding selector, will generate a seeding label in Auto Mode for user to mark 
    #
    self.seedingSelector = slicer.qMRMLNodeComboBox()
    self.seedingSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
    self.seedingSelector.selectNodeUponCreation = True
    self.seedingSelector.addEnabled = False
    self.seedingSelector.removeEnabled = False
    self.seedingSelector.setMRMLScene( slicer.mrmlScene )
    self.seedingSelector.setToolTip( "This seeding label will automatically create after you marking the ROI." )
    parametersFormLayout.addRow("Seeding ROI: ", self.seedingSelector)
    #
    # compensate Intensity for region growing algorithm, default is 11, this value controls the maximum and minimum intensity (intensity range) of region growing
    #
    self.compensateIntensitySlider = ctk.ctkSliderWidget()
    self.compensateIntensitySlider.singleStep = 1
    self.compensateIntensitySlider.minimum = 5
    self.compensateIntensitySlider.maximum = 50
    self.compensateIntensitySlider.value = 11 # Default value is 11, compensate 11 for intensity range is seems better from our experiements
    self.compensateIntensitySlider.setToolTip("Compensate some value to the intensity range of region growing algorithm.")
    parametersFormLayout.addRow("Compensate Value", self.compensateIntensitySlider)
    self.compensateIntensitySlider.connect('valueChanged(double)', self.onCompensateIntensityChanged)

    #
    # compensate Intensity for region growing algorithm, default is 11, this value controls the maximum and minimum intensity (intensity range) of region growing
    #
    self.smoothValueSlider = ctk.ctkSliderWidget()
    self.smoothValueSlider.singleStep = 1
    self.smoothValueSlider.minimum = 1
    self.smoothValueSlider.maximum = 60
    self.smoothValueSlider.value = 10 # Default value is 10, used for smooth the ROI when making 3D model
    self.smoothValueSlider.setToolTip("Smooth value for making 3D model.")
    parametersFormLayout.addRow("Smooth Value", self.smoothValueSlider)
    self.smoothValueSlider.connect('valueChanged(double)', self.onSmoothValueChanged)

    
    #
    # marker size, the pen size, user use the pen to mark initial ROI 
    #
    self.paintSizeSlider = ctk.ctkSliderWidget()
    self.paintSizeSlider.singleStep = 1
    self.paintSizeSlider.minimum = 1
    self.paintSizeSlider.maximum = 30
    self.paintSizeSlider.value = 5 # Default value is 5, the pen effect is "radius 5 cicle" by default
    self.paintSizeSlider.setToolTip("Set threshold value for the size of marker, marker is used to select label region.")
    parametersFormLayout.addRow("Marker Size", self.paintSizeSlider)
    self.paintSizeSlider.connect('valueChanged(double)', self.onMarkerSizeChanged)
    #
    # check box to trigger taking screen shots for later use 
    #
    self.enableFullAutoCheckBox = qt.QCheckBox()
    self.enableFullAutoCheckBox.checked = 1
    self.enableFullAutoCheckBox.enabled = True
    self.enableFullAutoCheckBox.setToolTip("If checked, automatically create a label map and automatically do segment after marking.")
    parametersFormLayout.addRow("Fully Auto Mode", self.enableFullAutoCheckBox)

    #
    #If checked, create a label map automatically for marking.
    #
    self.enableAutoLabelCheckBox = qt.QCheckBox()
    self.enableAutoLabelCheckBox.checked = 1
    self.enableAutoLabelCheckBox.enabled = False
    self.enableAutoLabelCheckBox.setToolTip("If checked, create a label map automatically for marking.")
    parametersFormLayout.addRow("Auto Create Label For Marking", self.enableAutoLabelCheckBox)
    
    #
    #If checked, create a 3D model automatically after segmentation completed.
    #
    self.enableAutoModelCheckBox = qt.QCheckBox()
    self.enableAutoModelCheckBox.checked = 1
    self.enableAutoModelCheckBox.enabled = False
    self.enableAutoModelCheckBox.setToolTip("If checked, create a 3D model automatically after segmentation completed.")
    parametersFormLayout.addRow("Auto Generate 3D Model", self.enableAutoModelCheckBox)
    
    #
    #If checked, automatically do segmentation after marking.
    #
    self.enableAutoSegmentCheckBox = qt.QCheckBox()
    self.enableAutoSegmentCheckBox.checked = 1
    self.enableAutoSegmentCheckBox.enabled = False
    self.enableAutoSegmentCheckBox.setToolTip("If checked, automatically do segmentation after marking.")
    parametersFormLayout.addRow("Auto Segment After Marking", self.enableAutoSegmentCheckBox)

    
    #
    # Apply Button, for manual operation
    #
    self.applyButton = qt.QPushButton("Manually Apply")
    self.applyButton.toolTip = "Run the segmentation manually."
    self.applyButton.enabled = False #unabled by default, this button will enable after uncheck Auto Mode
    parametersFormLayout.addRow(self.applyButton)


    # connections, process the event from UI

	
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.enableFullAutoCheckBox.connect('clicked(bool)', self.onFullAutoClicked)
    self.enableAutoSegmentCheckBox.connect('clicked(bool)', self.onAutoSegmentClicked)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    self.seedingSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

	
    crosshairNode=slicer.util.getNode('Crosshair') 
    
    #SegmentorLogic process the real segmentation
    self.logic = SegmentorLogic()
    
    self.labelNumber = 1 #default label number for marking

    #marker is for marking the initial seeds
    self.marker = Marker()
    self.marker.setup(self,self.paintSizeSlider.value,"Red")
    self.marker1 = Marker()
    self.marker1.setup(self,self.paintSizeSlider.value,"Yellow")
    self.marker2 = Marker()
    self.marker2.setup(self,self.paintSizeSlider.value,"Green")

    self.layout.addStretch(1)

    self.onSelect()
    global widgetForTest
    widgetForTest = self
    print "Setup processed!"

  #After the user entered this extension
  #We need to automatically create a label for user to marking(if Auto Mode and need to create that label)
  #Then we listen the events, such as mouse event, scene event
  def enter(self):
    self.createLabel()
    self.marker.listen() #marker will listen mouse event for processing marking, like button down, mouse move and release
    self.marker1.listen() 
    self.marker2.listen() 
    tag = self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneClose) 
    tag = self.addObserver(slicer.mrmlScene, vtk.vtkCommand.ModifiedEvent, self.updateLabelNode)
    self.onSelect();
    self.paintSizeSlider.enabled = True
    print "enter processed!"
    
  #
  #Remove mouse and scene listener after user leaved this extension
  #
  def exit(self):
    print "exit processed!"
    self.removeObservers()
    self.marker.dropListen()
    self.marker1.dropListen()
    self.marker2.dropListen()
    self.paintSizeSlider.enabled = False

  #
  #When scene closed, drop the listener
  #
  def onSceneClose(self, caller=None, event=None):
      print "onSceneClose"
      self.marker.dropListen()
      self.marker1.dropListen()
      self.marker2.dropListen()
      self.paintSizeSlider.enabled = False

  #
  #The marker will check wheather it is OK to process events
  #
  def enableEvent(self):
    if not self.applyButton.enabled and not self.enableAutoSegmentCheckBox.checked and not self.enableFullAutoCheckBox.checked:
        return False
    return True

  #
  #Marker would call this function after user have marked the seeds
  #
  def onEndPaint(self):
      if self.enableFullAutoCheckBox.checked or self.enableAutoSegmentCheckBox.checked:
        self.onApplyButton() # Do real segmentation

  #
  #Marker will call this function to get label node, marker will paint on this label
  #
  def onPaintBefore(self):
    labelNode = self.seedingSelector.currentNode()
    return labelNode

  #
  #Automatically create a label for user to mark, if Auto Create Label is checked
  #
  def createLabel(self):
    #only happens in the circumstances that input volume is selected but label volume is not created yet
    if self.inputSelector.currentNode():
       if not self.seedingSelector.currentNode():
         print "automatically create new label for marking"
         label = self.seedingSelector.currentNode()
         label = slicer.modules.volumes.logic().CreateAndAddLabelVolume(self.inputSelector.currentNode(),self.inputSelector.currentNode().GetName() + '-auto-label')
         #notify the Slicer that new label is created, set the new label as foreground label
         selectionNode = slicer.app.applicationLogic().GetSelectionNode()
         selectionNode.SetReferenceActiveLabelVolumeID(label.GetID())
         slicer.app.applicationLogic().PropagateVolumeSelection(0)

  #
  #After user reselect the input volume or changed the scene
  #
  def updateLabelNode(self, caller=None, event=None):
    #listen the event if label is not created
    if self.inputSelector.currentNode():
       if not self.seedingSelector.currentNode():
         self.marker.listen()
         self.marker1.listen()
         self.marker2.listen()
         self.paintSizeSlider.enabled = True

    #create the label if it is not created
    if not self.enableAutoLabelCheckBox.checked:
        return
    self.createLabel()
 
  #
  #Full Auto Model clicked
  #
  def onFullAutoClicked(self):
      self.enableAutoSegmentCheckBox.enabled = not self.enableFullAutoCheckBox.checked
      self.enableAutoLabelCheckBox.enabled = not self.enableFullAutoCheckBox.checked
      self.enableAutoModelCheckBox.enabled = not self.enableFullAutoCheckBox.checked

  #
  #Auto Segment clicked
  #
  def onAutoSegmentClicked(self):
      self.applyButton.enabled = not self.enableAutoSegmentCheckBox.checked

  #
  #To check whether is is OK to enable apply button
  #
  def onSelect(self):
    if self.enableFullAutoCheckBox.checked or self.enableAutoSegmentCheckBox.checked:
        self.applyButton.enabled = False
    else:
        self.applyButton.enabled = self.inputSelector.currentNode() and self.seedingSelector.currentNode()

  #
  #compensate intensity changed
  #
  def onCompensateIntensityChanged(self):
      print "compensate intensity ", self.compensateIntensitySlider.value
  #
  #smooth value changed
  #
  def onSmoothValueChanged(self):
      print "Smooth Value ", self.smoothValueSlider.value
  #
  #Change the marker size
  #
  def onMarkerSizeChanged(self):
    self.marker.dropListen()
    self.marker = Marker()
    self.marker.setMarkerSize(self.paintSizeSlider.value)
    self.marker.setup(self,self.paintSizeSlider.value,"Red")
    self.marker.listen()

    self.marker1.dropListen()
    self.marker1 = Marker()
    self.marker1.setMarkerSize(self.paintSizeSlider.value)
    self.marker1.setup(self,self.paintSizeSlider.value,"Yellow")
    self.marker1.listen()

    self.marker2.dropListen()
    self.marker2 = Marker()
    self.marker2.setMarkerSize(self.paintSizeSlider.value)
    self.marker2.setup(self,self.paintSizeSlider.value,"Green")
    self.marker2.listen()

    print "radius change to ", self.paintSizeSlider.value

  #
  #When user clicked apply button(only happens in manual mode) or called after marking completed (happens in auto mode).
  #
  def onApplyButton(self):
    auto_model = self.enableAutoModelCheckBox.checked
    full_auto = self.enableFullAutoCheckBox.checked
    paintSize = self.paintSizeSlider.value
    compensateIntensity = self.compensateIntensitySlider.value
    smoothValue = self.smoothValueSlider.value
    self.logic.run(self.inputSelector.currentNode(), self.seedingSelector.currentNode(), paintSize, auto_model or full_auto, compensateIntensity,self.labelNumber ,smoothValue)





#---------------------------------------------------------------------------
#
# Segmentor Test
#
class SegmentorTest(ScriptedLoadableModuleTest):

  def setUp(self):
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test()

  def test(self):

    self.delayDisplay("Starting the test")

    #load testing data
    scriptPath = os.path.dirname(os.path.abspath(__file__))
    if slicer.util.loadVolume:
      logging.info('Loading Testing/MRBrainTumor1.nrrd')
      slicer.util.loadVolume(scriptPath + "/Testing/MRBrainTumor1.nrrd")
    self.delayDisplay('Finished loading')

    #if extension loaded
    if widgetForTest:
        sliceWidget = slicer.app.layoutManager().sliceWidget("Yellow")
        renderWindow = sliceWidget.sliceView().renderWindow()
        #get size of the target window
        wid, hei = renderWindow.GetSize()
        print "size ", wid, hei
        #get paint point
        x = 0.39 * wid
        y = 0.63 * hei
        print "Testing paint at point ", x, y
        #paint the effect at that point
        widgetForTest.marker.testPaint(x,y)
        self.delayDisplay('Testing paint effect!')
        #apply the paint on label map
        widgetForTest.marker.testApplyPaint()
        self.delayDisplay('Testing applying paint effect!')
        #apply the painted label for segmentation
        widgetForTest.onApplyButton()
        self.delayDisplay('Testing segmentation!')

#---------------------------------------------------------------------------