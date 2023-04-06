#include <iostream>
#include <pcl/console/parse.h>
#include <pcl/ModelCoefficients.h>
#include <pcl/point_types.h>
#include <pcl/io/pcd_io.h>
#include <pcl/filters/project_inliers.h>
#include <pcl/filters/extract_indices.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/features/normal_3d.h>
#include <pcl/kdtree/kdtree.h>
#include <pcl/sample_consensus/method_types.h>
#include <pcl/sample_consensus/model_types.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl/segmentation/extract_clusters.h>
#include <pcl/surface/concave_hull.h>
#include <sys/stat.h>
#include <boost/filesystem.hpp>

std::string input_filename_ = ""; 	// "/home/ktw/Projects/pcd_pl/data/MapData_3_15_indoor_c.pcd";
std::string output_filename_ = ""; 	// "/home/ktw/Projects/pcd_pl/output/pcd_to_seg";
int maximum_iteration(100);
float threshold(0.11);
std::string filetype = "pcd";
float min_points_ratio(0.2);
std::string projection_on_plane = "true";

void showHelp(char *filename)
{
	std::cout << std::endl;
	std::cout << "************************" << std::endl;
	std::cout << "*                        *" << std::endl;
	std::cout << "* PCD PL - HELP          *" << std::endl;
	std::cout << "*                        *" << std::endl;
	std::cout << "***********************" << std::endl << std::endl;
	std::cout << "Usage: " << filename << " input.pcd outputname [Options]" << std::endl << std::endl;
	std::cout << "[Options] :" << std::endl;
	std::cout << "     --h:  Show this help." << std::endl;
	std::cout << "     --input: Input file" << std::endl;
	std::cout << "     --output: Output file" << std::endl;
	std::cout << "     --iteration : Set the maximum number of iterations before giving up(default 1000)" << std::endl;
	std::cout << "     --threshold : Distance to the model threshold(default 0.11)" << std::endl;
	std::cout << "     --projection :projection on model(true, false / default true)" << std::endl;
	std::cout << "     --output_type : File type(pcd, json / default pcd)" << std::endl;
	std::cout << "     --min_points_ratio :  min points ratio" << std::endl;
}

int parseCommandLine (int argc, char *argv[])
{
	//Show help
	if (pcl::console::find_switch (argc, argv, "-h"))
	{
		showHelp (argv[0]);
		return -1;
	}

	//General parameters
	pcl::console::parse_argument (argc, argv, "--input", input_filename_);
	pcl::console::parse_argument (argc, argv, "--output", output_filename_);
	pcl::console::parse_argument (argc, argv, "--iteration", maximum_iteration);
	pcl::console::parse_argument (argc, argv, "--threshold", threshold);
	pcl::console::parse_argument (argc, argv, "--projection", projection_on_plane);
	pcl::console::parse_argument (argc, argv, "--output_type", filetype);
	pcl::console::parse_argument (argc, argv, "--min_points_ratio", min_points_ratio);

	if(input_filename_.find(".pcd") == std::string::npos)
		input_filename_ = input_filename_ + ".pcd";

	std::cout << "input: " << input_filename_ << std::endl;
	std::cout << "output file tag: " << output_filename_ << std::endl;
	std::cout << "option: " << maximum_iteration << ", " << threshold << ", " << filetype;
	return 0; 
}

void WriteFile(std::string filename, pcl::PointCloud<pcl::PointXYZ> &cloud, std::string fileType, int nTailNum)
{
	pcl::PCDWriter writer;
	std::stringstream ss;

	if(fileType.compare("json") == 0)
	{
		ss << filename << "_@" << nTailNum << ".json";

		std::ofstream out(ss.str());
		out <<	" { \"type\": \"MultiPoint\", \n" ;
		out <<  "\"coordinates\"" << ": [ " ;
		for(int i = 0; i < cloud.size(); ++i)
		{
			if(i != 0)
				out << ", ";
			out << "[" << cloud[i].data[0] << ", " << cloud[i].data[1] << ", " <<cloud[i].data[2] << "] ";
		}
    	out << "]\n}";
		out.close();
	}
	else //not json
	{
		ss << filename << "_@"  << nTailNum << ".pcd";
		writer.write<pcl::PointXYZ> (ss.str (), cloud, false); 
	}
}

bool projectOnPlane(pcl::PointCloud<pcl::PointXYZ>::Ptr& cloud, pcl::ModelCoefficients::Ptr& coefficients, pcl::PointCloud<pcl::PointXYZ>::Ptr& cloud_projected)
{
	if(cloud->size() < 3)
		return false;

	pcl::ProjectInliers<pcl::PointXYZ> proj;
	proj.setModelType (pcl::SACMODEL_PLANE);
	proj.setInputCloud (cloud);
	proj.setModelCoefficients (coefficients);
	proj.filter(*cloud_projected);

	return true;
}

int main(int argc, char** argv)
{
	int ret = parseCommandLine (argc, argv);
	if(ret < 0)
		return -1;

	// Read in the cloud data
	pcl::PCDReader reader;
	pcl::PointCloud<pcl::PointXYZ>::Ptr cloud (new pcl::PointCloud<pcl::PointXYZ>), cloud_f (new pcl::PointCloud<pcl::PointXYZ>);
	reader.read (input_filename_, *cloud);
	
	// Create the segmentation object for the planar model and set all the parameters
	pcl::SACSegmentation<pcl::PointXYZ> seg;
	pcl::PointIndices::Ptr inliers (new pcl::PointIndices);
	pcl::ModelCoefficients::Ptr coefficients (new pcl::ModelCoefficients);
	pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_plane (new pcl::PointCloud<pcl::PointXYZ> ());
	
	seg.setOptimizeCoefficients (false);
	seg.setModelType (pcl::SACMODEL_PLANE);
	seg.setMethodType (pcl::SAC_RANSAC);
	seg.setMaxIterations (maximum_iteration);
	seg.setDistanceThreshold (threshold);
	
	int i=0, nr_points = (int) cloud->points.size ();
	int j = 0;
	
	std::string outFileName = output_filename_;
  	// boost::filesystem::create_directories(outFileName); // mkdir

	while (cloud->points.size () > min_points_ratio * nr_points)
	{
		// Segment the largest planar component from the remaining cloud
		seg.setInputCloud (cloud);
		seg.segment (*inliers, *coefficients);
		if (inliers->indices.size () == 0)
		{
			std::cout << "Could not estimate a planar model for the given dataset." << std::endl;
			break;
		}

		// Extract the planar inliers from the input cloud
		pcl::ExtractIndices<pcl::PointXYZ> extract;
		extract.setInputCloud (cloud);
		extract.setIndices (inliers);
		extract.setNegative (false);

		// Get the points associated with the planar surface
		extract.filter (*cloud_plane);
		std::cout << "PointCloud representing the planar component: " << cloud_plane->points.size () << " data points." << std::endl;

		// Remove the planar inliers, extract the rest
		extract.setNegative (true);
		extract.filter (*cloud_f);
		*cloud = *cloud_f;

		pcl::PointCloud<pcl::PointXYZ>::Ptr projected_cloud (new pcl::PointCloud<pcl::PointXYZ>);
		if(projection_on_plane == "true")
		{
			if(projectOnPlane(cloud_plane, coefficients, projected_cloud) == false)
				continue;
			cloud_plane = projected_cloud;
		}
		WriteFile(outFileName, *cloud_plane, filetype, j);
		
		j++;
	}

	return (0);
}