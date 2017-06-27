# Project - One Click Cut  - "To segment 3D ROI, like tumor, leison from given 3D volume"
# Author: Guoqing Bao
# Supervisor: Sidong Liu; Weidong Cai; 
# The University of Sydney
# 2017-05-08
#---------------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------------

import vtk, qt, ctk, slicer
import numpy as np

#---------------------------------------------------------------------------
#
# SegmentorUtils
#
class SegmentorUtils:
    # Numeric parameter input
    def numericInputFrame(self,parent, label, tooltip, minimum, maximum, step, decimals):
      inputFrame              = qt.QFrame(parent)
      inputFrame.setLayout(qt.QHBoxLayout())
      inputLabel              = qt.QLabel(label, inputFrame)
      inputLabel.setToolTip(tooltip)
      inputFrame.layout().addWidget(inputLabel)
      inputSpinBox            = qt.QDoubleSpinBox(inputFrame)
      inputSpinBox.setToolTip(tooltip)
      inputSpinBox.minimum    = minimum
      inputSpinBox.maximum    = maximum
      inputSpinBox.singleStep = step
      inputSpinBox.decimals   = decimals
      inputFrame.layout().addWidget(inputSpinBox)
      inputSlider             = ctk.ctkDoubleSlider(inputFrame)
      inputSlider.minimum     = minimum
      inputSlider.maximum     = maximum
      inputSlider.orientation = 1
      inputSlider.singleStep  = step
      inputSlider.setToolTip(tooltip)
      inputFrame.layout().addWidget(inputSlider)
      return inputFrame, inputSlider, inputSpinBox

    # define the cartesian function
    def cartesian(self, arrays, out = None):
        arrays = [np.asarray(x) for x in arrays]
        dtype = arrays[0].dtype    
        n = np.prod([x.size for x in arrays])
        if out is None:
            out = np.zeros([n, len(arrays)], dtype = dtype)    
        m = n / arrays[0].size
        out[:,0] = np.repeat(arrays[0], m)    
        if arrays[1:]:
            self.cartesian(arrays[1:], out = out[0:m, 1:])
            for j in xrange(1, arrays[0].size):
                out[j*m:(j+1)*m, 1:] = out[0:m, 1:]    
        return out

    # find the coordinates of new voxels
    def find_new_voxels(self, sx, sy, sz, iteration, out = None):

        new_voxel_coordinates_yz = self.cartesian((np.array([sx-iteration, sx+iteration]), \
                                          np.arange(sy-iteration, sy+iteration+1), \
                                          np.arange(sz-iteration, sz+iteration+1)))

        new_voxel_coordinates_xz = self.cartesian((np.arange(sx-iteration+1, sx+iteration), \
                                          np.array([sy-iteration, sy+iteration]), \
                                          np.arange(sz-iteration, sz+iteration+1)))

        new_voxel_coordinates_xy = self.cartesian((np.arange(sx-iteration+1, sx+iteration), \
                                          np.arange(sy-iteration+1, sy+iteration), \
                                          np.array([sz-iteration, sz+iteration])))

        new_voxel_coordinates = np.concatenate((new_voxel_coordinates_yz, np.concatenate((new_voxel_coordinates_xz, new_voxel_coordinates_xy))))
        return new_voxel_coordinates

