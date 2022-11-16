// name = PCD density
// programmer = developed by KTW(laputa99999@gmail.com)
// purpose = calculate point cloud density
// date = 2022.2.20
// todo = kNN, area density, volume density
// 
#include <stdio.h>
#include <iostream>
#include <pcl/PCLPointCloud2.h>
#include <pcl/io/pcd_io.h>
#include <pcl/features/normal_3d.h>
#include <pcl/point_types.h>
#include <pcl/io/pcd_io.h>
#include <pcl/kdtree/kdtree_flann.h>

using namespace pcl;
using namespace pcl::io;
using namespace pcl::console;

typedef pcl::PointXYZI PointT;

float G(float x, float sigma)
{
  return std::exp (- (x*x)/(2*sigma*sigma));
}

float calcVolumeDensity(std::vector<float>& dists)
{
  int N = dists.size();
  if(N == 0)
    return 0.0;
  
  // the number of neighbors N (only available in 'Precise' mode)
  // surface density: number of neighbors divided by the neighborhood surface = N / (Pi.R2)
  // volume density: number of neighbors divided by the neighborhood volume = N / (4/3.Pi.R3)
  float radius = 0.0;
  for(std::vector<float>::iterator i = dists.begin(); i != dists.end(); i++)
  {
    float d = *i;
    radius = radius + d;
  }
  radius /= (float)N;

  // density 2D
  float density = float(N) / (M_PI * pow(radius, 2.0)); // 1 / circle area 
  return density;

  /* https://www.mathworks.com/matlabcentral/answers/563603-how-to-compute-the-density-of-a-3d-point-cloud
  AllPoints = % your points
  K = 1;
  for idx=1:length(AllPoints)
  [~,r] = findNearestNeighbors(AllPoints,AllPoints(idx,:),K);
  density(idx) = 1/(4*pi*r.^3/3);
  end
  */
}

int main (int argc, char *argv[])
{
  std::string incloudfile = argv[1];
  std::string outcloudfile = argv[2];
  int N = atoi(argv[3]);
  // float queryRadius = 1.0;

  // Load cloud
  pcl::PointCloud<PointT>::Ptr cloud (new pcl::PointCloud<PointT>);
  pcl::io::loadPCDFile (incloudfile.c_str (), *cloud);
  int pnumber = (int)cloud->size ();

  // Output Cloud = Input Cloud
  pcl::PointCloud<PointT> outcloud = *cloud;

  // Set up KDTree
  pcl::KdTreeFLANN<PointT>::Ptr tree (new pcl::KdTreeFLANN<PointT>);
  tree->setInputCloud (cloud);

  // Neighbors containers
  std::vector<int> k_indices;
  std::vector<float> k_distances;

  // Main Loop
  for (int point_id = 0; point_id < pnumber; ++point_id)
  {
    PointT point = outcloud[point_id];
    tree->nearestKSearch(point, N, k_indices, k_distances);

    float density = calcVolumeDensity(k_distances);
    outcloud[point_id].intensity = density;
  }

  // Save filtered output
  pcl::io::savePCDFile (outcloudfile.c_str (), outcloud);
  return (0);
}