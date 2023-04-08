# build PCL library
sudo apt-get install build-essential g++ python3-dev autotools-dev libicu-dev libbz2-dev libboost-all-dev
sudo apt install libeigen3-dev
dpkg -L libeigen3-dev
sudo apt-get install -y libflann-dev
sudo apt-get install libpcap-dev
sudo apt-get install libgl1-mesa-dev
sudo apt install qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools
sudo apt install clang-format
sudo apt-get install libusb-1.0-0-dev
sudo apt install libvtk9.1

git clone https://github.com/PointCloudLibrary/pcl pcl-trunk
cd pcl-trunk && mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ..
make -j2
sudo make -j2 install
