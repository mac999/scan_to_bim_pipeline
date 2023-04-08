# PCD pipeline
# developed by KTW(laputa99999@gmail.com)
# set default env varibles
cmake_minimum_required(VERSION 3.16.1)

set(SUBSYS_NAME pcd_pipeline)
set(SUBSYS_DESC "Useful PCD pipeline command")
set(DEFAULT ON)
set(REASON "")
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/../bin)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/../bin)
#set(DESTINATION_OUTPUT_PATH ${CMAKE_BINARY_DIR}/../bin)
set(PCL_ROOT "/home/ktw/projects/pcl-1.13")
set(VTK_INC "/usr/include/vtk-7.1")
set(USR_LIB "/usr/lib/x86_64-linux-gnu")

message("BIN PATH = " ${CMAKE_BINARY_DIR})
message("PCL ROOT = " ${PCL_ROOT}/common/include)
message("VTK INC = " ${VTK_INC})

# set project
project(pcd_pipeline)

# set include and library
include_directories(PUBLIC ${PCL_ROOT}/common/include ${PCL_ROOT}/features/include ${PCL_ROOT}/filters/include ${PCL_ROOT}/geometry/include ${PCL_ROOT}/io/include ${PCL_ROOT}/kdtree/include ${PCL_ROOT}/keypoints/include ${PCL_ROOT}/octree/include ${PCL_ROOT}/recognition/include ${PCL_ROOT}/registration/include ${PCL_ROOT}/sample_consensus/include ${PCL_ROOT}/search/include ${PCL_ROOT}/segmentation/include ${PCL_ROOT}/visualization/include ${PCL_ROOT}/surface/include ${PCL_ROOT}/build/include /usr/include/eigen3 ${VTK_INC})

link_directories(${PCL_ROOT}/build/lib/ ${USR_LIB})
link_libraries(libpcl_common.so libpcl_features.so libpcl_io.so libpcl_kdtree.so libpcl_common.so libpcl_ml.so libpcl_keypoints.so libpcl_octree.so libpcl_outofcore.so libpcl_recognition.so libpcl_registration.so libpcl_sample_consensus.so libpcl_segmentation.so libpcl_search.so libpcl_surface.so libpcl_surface.so libpcl_visualization.so libpcl_filters.so libboost_filesystem.so libvtkIOLegacy-7.1.so libvtkCommonExecutionModel-7.1.so libvtkCommonDataModel-7.1.so libvtkCommonCore-7.1.so libvtkRenderingLOD-7.1.so libvtkRenderingAnnotation-7.1.so libvtkRenderingFreeType-7.1.so libvtkRenderingCore-7.1.so libvtkFiltersSources-7.1.so libvtkFiltersCore-7.1.so libvtkCommonMath-7.1.so libboost_program_options.so)

# program
add_executable(pcd_density ./pcd_density/pcd_density.cpp)
add_executable(pcd_normal ./pcd_normal/pcd_normal.cpp)
add_executable(pcd_viewer ./pcd_viewer/pcd_viewer.cpp)
# add_executable(pcd_to_plane ./pcd_to_plane/pcd_to_plane.cpp)
add_executable(pcd_to_seg ./pcd_to_seg/pcd_to_seg.cpp)
add_executable(seg_to_geo ./seg_to_geo/seg_to_geo.cpp)

# copy binary files
# file(COPY ${CMAKE_RUNTIME_OUTPUT_DIRECTORY} DESTINATION ${DESTINATION_OUTPUT_PATH})
