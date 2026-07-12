# PCD pipeline
# developed by KTW(laputa99999@gmail.com)
cmake_minimum_required(VERSION 3.16.1)

project(pcd_pipeline)

set(SUBSYS_NAME pcd_pipeline)
set(SUBSYS_DESC "Useful PCD pipeline command")
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT MSVC)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
endif()
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/../bin)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/../bin)

message("BIN PATH = " ${CMAKE_BINARY_DIR})

# Locate PCL (pulls in Boost, Eigen, FLANN and VTK transitively).
# If PCL was built from source without installing, pass its build dir:
#   cmake -DPCL_DIR=/path/to/pcl/build ..
find_package(PCL 1.12 REQUIRED COMPONENTS common features filters io kdtree keypoints octree recognition registration sample_consensus search segmentation surface visualization)
find_package(Boost REQUIRED COMPONENTS filesystem program_options)

include_directories(${PCL_INCLUDE_DIRS} ${Boost_INCLUDE_DIRS})
link_directories(${PCL_LIBRARY_DIRS})
add_definitions(${PCL_DEFINITIONS})

# program modules. each stage is an independent executable so new stages can be added easily.
add_executable(pcd_density ./pcd_density/pcd_density.cpp)
target_link_libraries(pcd_density ${PCL_LIBRARIES})

add_executable(pcd_to_seg ./pcd_to_seg/pcd_to_seg.cpp)
target_link_libraries(pcd_to_seg ${PCL_LIBRARIES} Boost::filesystem)

add_executable(seg_to_geo ./seg_to_geo/seg_to_geo.cpp)
target_link_libraries(seg_to_geo ${PCL_LIBRARIES} Boost::filesystem)

# optional modules. only built when the source file exists in the working tree.
foreach(optional_module pcd_normal pcd_viewer pcd_to_plane)
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${optional_module}/${optional_module}.cpp)
        add_executable(${optional_module} ./${optional_module}/${optional_module}.cpp)
        target_link_libraries(${optional_module} ${PCL_LIBRARIES})
    endif()
endforeach()
