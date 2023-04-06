# Scan to BIM project 
Scan to BIM pipieline to convert 3D scan data (point cloud data) to BIM objects.

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
1. install python, pip</br>
https://phoenixnap.com/kb/how-to-install-python-3-ubuntu</br>
2. install gdal</br>
https://mothergeo-py.readthedocs.io/en/latest/development/how-to/gdal-ubuntu-pkg.html</br>
3. install pdal</br>
https://installati.one/install-pdal-ubuntu-20-04/</br>
4. install cuda, tensorflow, pytorch</br>
5. install cmake</br>
https://www.cyberithub.com/how-to-install-cmake-on-ubuntu-20-04-lts-focal-fossa/</br>

# PCL installation
In addition, if you use PCL, install the below package.</br>
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
In terminal, input the below commands. </br>
git clone https://github.com/mac999/scan_to_bim_pipeline</br>
cd scan_to_bim_pipeline</br>
pip -r install requirements.txt</br>
mkdir build</br>
cmake ..</br>
make</br>
</br>
If there are depandency errors in requirements.txt, use requirements_simple.txt.

# run
design pipeline by using SBDL(scan to bim description language) formatted by JSON like below.</br>
TBD</br>
</br>
cd pipeline</br>
python app.py</br>

# license
MIT license

# developed by 
KICT, IUPUI / Pudue / UNF univesity

# reference
Kang, T., Patil, S., Kang, K., Koo, D. and Kim, J., 2020. Rule-based scan-to-BIM mapping pipeline in the plumbing system. Applied Sciences, 10(21), p.7422. https://www.mdpi.com/2076-3417/10/21/7422
