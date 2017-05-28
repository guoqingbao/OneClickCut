cmake_minimum_required(VERSION 2.8.9)

project(OneClickCut)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/OneClickCut")
set(EXTENSION_CATEGORY "Segmentation")
set(EXTENSION_CONTRIBUTORS "Guoqing Bao (The University of Sydney)")
set(EXTENSION_DESCRIPTION "This extension implement the one-click-cut segmentation in 3D volume.
    After you load the volume, use the marker to mark the region you are interested, 
    this extension will automatically segment the ROI(include surrounding similar regions),
    then a 3D model of your ROI will automatically build.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/OneClickCut.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/OneClickCut/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any


#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(Segmentor)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
