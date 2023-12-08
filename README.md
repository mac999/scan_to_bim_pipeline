# Scan to BIM project 
Scan to BIM pipieline to convert 3D scan data (point cloud data) to BIM objects.

# description
Scan to BIM research project has purpose like below.</br>
</br>
1. 3D point cloud processsing pipeline implementation dynamically using simple SBDL(Scan to BIM Description Language. JSON format).</br>
2. Classification of outdoor building objects such as wall (facade), road etc. </br> 
3. Extraction geometry information from classification.</br>
4. Binding BIM object with geometry information and property set.</br>
</br>
<p align="center">
<img height="200" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept1.JPG"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept2.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/ifc_building_facade.jpg"/></br>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/perform.PNG"/>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/perform2.PNG"/></br>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_scan.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_BIM.PNG"/>
</p>

# version history
v0.1</br>
> 2022.11, Scan to BIM pipeline framework released. Simple SBDL was developed considering geometry computation algorithms to extract outdoor facade object, deep learning, docker based component etc. 

v0.2</br>
> 2023.7, Docker image support. pipeline revision for multiple input files processing. refactoring.</br>
> 2023.8, [Data augumentation tool](https://github.com/mac999/pcd_augmentation)</br>
> 2023.9. [LiDAR simulation tool](https://github.com/mac999/simulate_LiDAR)</br>
> 2023.10. [3D scan data quality checker tool](https://github.com/mac999/check_scan_quality).</br>

# furture update plan
v0.3</br>
> 2023.12, documentation to use SBDL.</br>
> 2023.12, simple MLOps codes for outdoor object train.</br>
</br>

v0.4</br>
> 2024.2, SBDL enhancement to supporting VFP(Visual Flow Programming) or LLM(Large Language Model. ex. ChatGPT).</br>
> 2024.3, Update indoor Object Mapping support.</br>
> MLOps support.</br>
> Simple Scan Data Processing App using Scan to BIM application.</br>
<p>1) deep learing based indoor classification. 2) PCD indoor segmentation. 3) segment to geometry using ML. 4) geometry to BIM using revit plugin. 5) 3D data argumentation. 6) LiDAR simuation 7) 3D PCD quality check</p></br>
<center><p><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_ml.JPG"/></p></center>

v0.5</br>
> update PCD to DTM, DTM to Geometry, Geometry to BIM object source files.</br>

# setup development environment & packages 
1. install python, pip</br>
https://phoenixnap.com/kb/how-to-install-python-3-ubuntu</br>
2. install cmake</br>
https://www.cyberithub.com/how-to-install-cmake-on-ubuntu-20-04-lts-focal-fossa/</br>
3. install [cuda](https://developer.nvidia.com/cuda-toolkit-archive), [tensorflow](https://www.tensorflow.org/install?hl=ko), [pytorch](https://pytorch.org/get-started/locally/)</br>
4. install gdal</br>
https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html</br>
5. install pdal</br>
https://installati.one/install-pdal-ubuntu-20-04/</br>
In terminal, run 'pdal' command. If there is error 'libgdal.so.29: cannot open shared object file', run the below command to make linked file name.</br>
sudo ln -s libgdal.so.30 libgdal.so.29</br>
if there is error in prebuild pdal, download, build and install pdal source files of github 
https://github.com/PDAL/PDAL</br>
6. install ifcopenshell</br>
https://pypi.org/project/ifcopenshell/0.7.0.230418/</br>
https://blenderbim.org/docs-python/ifcopenshell-python/installation.html</br>
7. build docker image</br>
cd docker</br>
cd build_docker_open3d</br>
bash build_docker.sh</br>

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
Before run, install requirements_simple.txt(or requirements.txt) including the above packages.</br>
1. modify /pipeline/config.json considering your input, output folder path. In reference, root foler name is scan_to_bim_pipeline which you downloaded and installed from github.</br>
```
{
    "app": "pcd_pipeline",
    "root_path": "./pipeline/",
    "bin_path": "./",
    "lib_path": "./lib/",
    "data_path": "./input/",
    "debug_gui": false
}
```
2. download input sample files and copy them into ./input folder. refer to [sample dataset](https://drive.google.com/drive/folders/1Jb32VkVEuhkKKZ8XVE9E8RLUw2S-VfSd).</br>
3. run app.py like below.</br>
python ./pipeline/app.py</br>
<img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/result_outdoor.PNG"/></br>
4. Or design pipeline by using SBDL(scan to bim description language) formatted by JSON like below.</br>
  pipeline.[name]={stage*}</br>
  stage={module_type, parameters}</br>
  parameters={name, value}*</br>
  module_type={python program | docker image | binary executable program}</br>
  * parameters should be defined in module before usage.</br>
  condition={"in_stage_return", "out_stage_return"}</br></br>

In scan to BIM pipeline using SBDL example, </br>
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

# sample dataset
Download dataset and copy to /input folder.</br> 
3D point cloud sample file [download](https://drive.google.com/drive/folders/1Jb32VkVEuhkKKZ8XVE9E8RLUw2S-VfSd)</br>

# architecture
SBDL concept diagram and [UML](https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/SAD.uml) architecture.</br>
<p align="center"><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml3.PNG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml1.PNG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/uml2.PNG"/></p>

# license
MIT license.</br></br>
Acknowledge.</br>
> Scan To BIM Technology Development 3D Urban Building Model Process Automation, 2022</br>
> 3D vision & AI based Indoor object Scan to BIM pipeline for building facility management, 2023</br>
Funded by KICT</br></br>
Organization Roles</br>
> KICT: Scan to BIM pipeline architecture design, algorithm programming, test, code management</br></br>
Specially, Thanks for contribution like below</br>
> IUPUI (Prof. Koo Dan, Prof. Kwonsik Song), UNF (Prof. Jonghoon Kim: usecase, code, policy survey</br>
> Purdue University (Prof. Kyubyung Kang): deep learning train, dataset collection, labeling, analysis</br>
> Stony Brook University (Prof. Jongsung Choi): data collection using SLAM, labeling, analysis</br>
</br>
Kang, T., Patil, S., Kang, K., Koo, D. and Kim, J., 2020. Rule-based scan-to-BIM mapping pipeline in the plumbing system. Applied Sciences, 10(21), p.7422. https://www.mdpi.com/2076-3417/10/21/7422
