# Scan to BIM project 
Scan to BIM pipieline to convert 3D scan data (point cloud data) to BIM objects.

# description
Scan to BIM project has purpose like below. 

1. 3D point cloud processsing pipeline implementation dynamically using simple SBDL(Scan to BIM Description Language. JSON format).
2. Classification of outdoor building objects such as wall (facade), road etc. 
3. Extraction geometry information from classification.
4. Binding BIM object with geometry information and property set.

<p align="center">
<img height="200" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept1.JPG"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept2.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/ifc_building_facade.jpg"/></br>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/perform.PNG"/>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/perform2.PNG"/></br>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_scan.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_BIM.PNG"/>
</p>

# version history
v0.1</br>
> Scan to BIM pipeline framework released. Simple SBDL was developed considering geometry computation algorithms to extract outdoor facade object, deep learning, docker based component etc. 

# furture research & development plan
v0.3</br>
> documentation to use SBDL.</br>
> Simple MLOps support for outdoor object train.</br>
</br>

v0.5</br>
> SBDL enhancement to supporting VFP(Visual Flow Programming) or LLM(Large Language Model. ex. ChatGPT).</br>
> VFP support.</br>
> Indoor Object Mapping support.</br>
> MLOps support.</br>
> Simple Scan Data Processing App using Scan to BIM application.</br>

# setup development environment & packages 
1. install python, pip</br>
https://phoenixnap.com/kb/how-to-install-python-3-ubuntu</br>
2. install gdal</br>
https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html</br>
3. install pdal</br>
https://installati.one/install-pdal-ubuntu-20-04/</br>
In terminal, run 'pdal' command. If there is error 'libgdal.so.29: cannot open shared object file', run the below command to make linked file name.</br>
sudo ln -s libgdal.so.30 libgdal.so.29</br>
4. install [cuda](https://developer.nvidia.com/cuda-toolkit-archive), [tensorflow](https://www.tensorflow.org/install?hl=ko), [pytorch](https://pytorch.org/get-started/locally/)</br>
5. install cmake</br>
https://www.cyberithub.com/how-to-install-cmake-on-ubuntu-20-04-lts-focal-fossa/</br>

# PCL installation
In addition, if you use PCL, run the below commands for installing package or 'sh [build_pcl.sh](https://github.com/mac999/scan_to_bim_pipeline/blob/main/build_pcl.sh)'.</br>
sudo apt-get install build-essential g++ python3-dev autotools-dev libicu-dev libbz2-dev libboost-all-dev</br>
sudo apt install libeigen3-dev</br>
dpkg -L libeigen3-dev</br>
sudo apt-get install -y libflann-dev</br>
sudo apt-get install libpcap-dev</br>
sudo apt-get install libgl1-mesa-dev</br>
sudo apt install qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools</br>
sudo apt install clang-format</br>
sudo apt-get install libusb-1.0-0-dev</br>
sudo apt install libvtk9.1</br></br>
git clone https://github.com/PointCloudLibrary/pcl pcl-trunk</br>
cd pcl-trunk && mkdir build && cd build</br>
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ..</br>
make -j2</br>
sudo make -j2 install</br>

In detail, refer to </br>
https://github.com/PointCloudLibrary/pcl</br>
https://pcl.readthedocs.io/projects/tutorials/en/latest/compiling_pcl_posix.html</br>

# build & installation
Modify the below PCL_ROOT(PCL library path), VTK_INC(VTK include path), USR_LIB paths in [CMakeLists.txt](https://github.com/mac999/scan_to_bim_pipeline/blob/main/CMakeLists.txt) properly. In reference, PCL-1.13 has an memory error (handmade_aligned_free) related to eigen library(2023/4/10).</br>
set(PCL_ROOT "/home/ktw/projects/pcl-1.12")</br>
set(VTK_INC "/usr/include/vtk-7.1")</br>
set(USR_LIB "/usr/lib/x86_64-linux-gnu")</br>
</br>
In terminal, input the below commands. </br>
git clone https://github.com/mac999/scan_to_bim_pipeline</br>
cd scan_to_bim_pipeline</br>
pip -r install requirements.txt</br>
sudo apt install clang</br>
mkdir build</br>
cmake ..</br>
make</br>
</br>
If there are depandency errors in requirements.txt, use requirements_simple.txt.

# run
design pipeline by using SBDL(scan to bim description language) formatted by JSON like below.</br>
  pipeline.[name]={stage*}</br>
  stage={module_type, parameters}</br>
  module_type={python program | docker image | binary executable program}</br></br>
In scan to BIM pipeline example, </br>
pipeline.indoor_obb_extraction = data_to_format > pcd_to_seg > pcd_to_clean > seg_to_geo</br>
pipeline.indoor_obb_extraction(*.las) > *.geojson</br>
</br>
```
{
    "pipeline.indoor_obb_extraction": [
        {
            "type": "data_to_format",
            "output_type": ".pcd"
        },
        {
            "type": "pcd_to_seg",
            "iteration": "1000", 
            "threshold": "0.1",
            "projection": "true",
            "remove_overlap_distance": "0.10",
            "min_points_ratio": "0.2"
        },
        {
            "type": "pcd_to_clean",
            "voxel_down_size": "0.0",
            "nb_radius_points": "50",
            "nb_radius": "0.1"
        },
        {
            "type":"seg_to_geo",
            "alpha": "0.15"
        }
    ]
}
```
</br>
cd pipeline</br>
python app.py</br>

# architecture
SBDL concept diagram and [UML](https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/SAD.uml) architecture.</br>
<p align="center"><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml3.PNG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml1.PNG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml2.PNG"/></p>

# license
MIT license

# developed by 
KICT, IUPUI / Pudue / UNF univesity

# reference
Kang, T., Patil, S., Kang, K., Koo, D. and Kim, J., 2020. Rule-based scan-to-BIM mapping pipeline in the plumbing system. Applied Sciences, 10(21), p.7422. https://www.mdpi.com/2076-3417/10/21/7422
