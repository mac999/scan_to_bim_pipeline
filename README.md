# project 
Scan to BIM pipieline 

# description
Scan to BIM project has purpose like below. 

1. 3D point cloud processsing pipeline implementation dynamically using JSON.
2. Classification of outdoor building objects such as wall (facade), road etc. 
3. Extraction geometry information from classification.
4. Binding BIM object with geometry information and property set.

<p align="center">
<img height="200" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept1.JPG"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept2.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/ifc_building_facade.jpg"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_scan.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_BIM.PNG"/></p>

# version history
0.1: Scan to BIM framework released. This pipeline used geometry computation algorithms, deep learning etc. 

# setup development environment & packages 
1. git clone https://github.com/mac999/scan_to_bim_pipeline
2. install python, pip
https://phoenixnap.com/kb/how-to-install-python-3-ubuntu
3. install gdal
https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html
4. install pdal
https://installati.one/install-pdal-ubuntu-20-04/
5. install cuda, tensorflow, pytorch
6. install cmake
https://www.cyberithub.com/how-to-install-cmake-on-ubuntu-20-04-lts-focal-fossa/

# build & installation
In addition, if you use PCL, install PCL library by using CMake like below. 
1. compile and install PCL (https://github.com/PointCloudLibrary/pcl)
2. cd scan_to_bim_pipeline
3. pip -r install requirements.txt
4. mkdir build
5. cmake ..
6. make

# license
MIT license

# developed by 
KICT, IUPUI / Pudue / UNF univesity

# reference
Kang, T., Patil, S., Kang, K., Koo, D. and Kim, J., 2020. Rule-based scan-to-BIM mapping pipeline in the plumbing system. Applied Sciences, 10(21), p.7422. https://www.mdpi.com/2076-3417/10/21/7422
