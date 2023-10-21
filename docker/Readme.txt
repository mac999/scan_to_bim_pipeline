PCD_PL uses docker image with Tensorflow, Torch, Open3D using GPU.
In build_docker_open3d, you can use Dockerfile for build the docker image. 

1. Install docker 

2. Install NVIDIA driver
ubuntu-drivers devices
sudo apt install nvidia-driver-[your driver version]
ex) sudo apt install nvidia-driver-515
sudo reboot
nvidia-smi

3. install NVIDIA driver, docker toolkits. refer to https://medium.com/@linhlinhle997/how-to-install-docker-and-nvidia-docker-2-0-on-ubuntu-18-04-da3eac6ec494

distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
      && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
      && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
            sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
            sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2

4. build docker image
run bash bulid_docker.sh

5. mount dataset for training
In example, run pcd_to_seg_ml/mount_train_data_from_media.sh
Considering your environment, modify and use it. 

6. run docker image
In example, run docker_ml_open3d_data_debug.sh

In addition, there is error in dataprocessing.py of open3d. fix it using pcd_to_seg_ml/fixed_open3dml_error/fix_open3dml.sh

7. run python code which uses open3d.ml with GPU
In example, pcd_to_seg_ml/pcd_to_seg_ml.py, train_pcd_on_torch.py, update_pcd_normal.py

- developed by taewook kang, 2022. 