#include <iostream>
#include <pcl/console/parse.h>
#include <pcl/ModelCoefficients.h>
#include <pcl/point_types.h>
#include <pcl/io/pcd_io.h>
#include <pcl/filters/extract_indices.h>
#include <pcl/filters/voxel_grid.h>
#include <pcl/features/normal_3d.h>
#include <pcl/kdtree/kdtree.h>
#include <pcl/sample_consensus/method_types.h>
#include <pcl/sample_consensus/model_types.h>
#include <pcl/segmentation/sac_segmentation.h>
#include <pcl/segmentation/extract_clusters.h>
#include <pcl/surface/concave_hull.h>
#include <pcl/surface/convex_hull.h>
#include <boost/filesystem.hpp>
#include <boost/range/iterator_range.hpp>
#include <iostream>
#include <string>
#include <vector>

using namespace std;
using namespace boost::filesystem;

std::string input_filename_ = "/home/ktw/Projects/pcd_pl/output/pcd_to_seg*.pcd";
std::string output_filename_ = "/home/ktw/Projects/pcd_pl/output/seg_to_geo";
std::string hulltype = "cc";
std::string filetype = "pcd";
float alpha = 0.15; // 0.1; // 0.2; // 0.1

void showHelp (char *filename)
{
  std::cout << std::endl;
  std::cout << "************************" << std::endl;
  std::cout << "*                        *" << std::endl;
  std::cout << "* PCD PIPELINE - HELP *" << std::endl;
  std::cout << "*                        *" << std::endl;
  std::cout << "***********************" << std::endl << std::endl;
  std::cout << "Usage: " << filename << " inputfoldername outputfoldername [Options]" << std::endl << std::endl;
  std::cout << "[Options] :" << std::endl;
  std::cout << "     --h:  Show this help." << std::endl;
  std::cout << "     --input: Input file" << std::endl;
  std::cout << "     --output: Output file" << std::endl;  
  std::cout << "     --hull_type :  Hull Type(cc -concave, cv - convex / default cc)" << std::endl;
  std::cout << "     --alpha :  concave alpha value" << std::endl;
  std::cout << "     --output_type :  File type(pcd , json / default pcd)" << std::endl;
}

void parseCommandLine (int argc, char *argv[])
{
  //Show help
  if (argc <= 1 || pcl::console::find_switch (argc, argv, "-h"))
  {
    showHelp (argv[0]);
    exit (0);
  }

  //General parameters
  pcl::console::parse_argument (argc, argv, "--input", input_filename_);
  pcl::console::parse_argument (argc, argv, "--output", output_filename_);  
  pcl::console::parse_argument (argc, argv, "--hull_type", hulltype);
  pcl::console::parse_argument (argc, argv, "--output_type", filetype);
  pcl::console::parse_argument (argc, argv, "--alpha", alpha);

  std::cout << "input: " << input_filename_ << std::endl;
  std::cout << "output file tag: " << output_filename_ << std::endl;
  std::cout << "alpha: " << alpha << std::endl;
}

void WriteJSONFile(std::string filename, pcl::PointCloud<pcl::PointXYZ> &cloud, std::vector<pcl::Vertices> &polygons, int nTailNum)
{
	pcl::PCDWriter writer;
	std::stringstream ss;
	ss << filename << "_@"<< nTailNum << ".json";
	std::ofstream out(ss.str());

	out <<	" { \"type\": \"MultiPolygon\", \n" ;
	out <<  "\"coordinates\"" << ": [ \n" ;

	for(auto it = polygons.begin(); it != polygons.end(); ++it)
	{
		if(it != polygons.begin())
			out << ", \n";
		out << "[[";
		for(unsigned int i = 0; i < (*it).vertices.size(); ++i)
		{
			if(i != 0)
				out << ", ";
			out << "[" << cloud[(*it).vertices[i]].data[0] << ", " << cloud[(*it).vertices[i]].data[1]  << ", " << cloud[(*it).vertices[i]].data[2] << "]";
		}
		out << ",[" << cloud[(*it).vertices[0]].data[0] << ", " << cloud[(*it).vertices[0]].data[1]  << ", " << cloud[(*it).vertices[0]].data[2] << "]";
		out << "]]";
	}
	out << "]\n}";

	out.close();
}


void WritePCDFile(std::string filename, pcl::PointCloud<pcl::PointXYZ> &cloud, int nTailNum)
{
	pcl::PCDWriter writer;
	std::stringstream ss;
	ss << filename << "_@"<< nTailNum << ".pcd";
	writer.write<pcl::PointXYZ> (ss.str (), cloud, false); 
}

std::string getFileExtension(std::string filePath)
{
    path pathObj(filePath);
    if (pathObj.has_extension()) {
        return pathObj.extension().string();
    }
    return "";
}

bool isMatchFile(string fname, string name)
{
	bool ret = true;
	for(int i = 0; i < (int)fname.length() && i < (int)name.length(); i++)
	{
		if(fname[i] == '*')
			return ret;
		if(fname[i] != name[i])
			ret = false;
	}
	return false;
}

void getFileNames(string pathname, vector<string>& filenames)
{
	path p(pathname);
	std::string fname = p.filename().c_str();
	std::string ext = p.extension().string();
	std::string dir = p.parent_path().c_str();

	boost::filesystem::directory_iterator i(dir), end;
	for (; i != end; ++i)
  {
		path curfile = (*i).path();
		if(curfile.extension() != ext)
			continue;

		std::string fname2 = curfile.filename().c_str();
		if(isMatchFile(fname, fname2) == false)
			continue;

		std::string name = curfile.c_str();
		filenames.push_back(name);
	}
}

int get_file_index(std::string fname)
{
  path p(fname);
	std::string name = p.filename().c_str();
	std::string ext = p.extension().string();

	std::size_t found = name.rfind("_@");
	std::string num = name.substr(found + 2, name.length() - ext.length() - found - 1);
	int index = atoi(num.c_str());	
	return index;
}

int main(int argc, char** argv)
{
	parseCommandLine (argc, argv);

	pcl::PCDWriter writer;
	std::string strFolderName = input_filename_ + "*.pcd";
	std::vector<std::string> vecFileNames;

	std::cout << "input folder: " << strFolderName << std::endl;
	getFileNames(strFolderName, vecFileNames);	// TBD.

  	std::cout << "input file count: " << vecFileNames.size() << std::endl;
  
	// boost::filesystem::create_directories(output_filename_.c_str());
	int index = 0;
	for(auto it  = vecFileNames.begin(); it != vecFileNames.end(); ++it)
	{
		pcl::PCDReader reader;
		pcl::PointCloud<pcl::PointXYZ>::Ptr cloud (new pcl::PointCloud<pcl::PointXYZ>), cloud_f (new pcl::PointCloud<pcl::PointXYZ>);

		std::string fname = *it;

	  	std::cout << "input file: " << fname << std::endl;

		index = get_file_index(fname);
		reader.read (*it, *cloud);

		pcl::ConcaveHull<pcl::PointXYZ> concave;
		pcl::ConvexHull<pcl::PointXYZ> convex;
		pcl::PointCloud<pcl::PointXYZ>::Ptr cloud_hull (new pcl::PointCloud<pcl::PointXYZ>);
		std::vector<pcl::Vertices> polygons;
		if(hulltype.compare("cc") == 0)
		{
			concave.setInputCloud (cloud);
			concave.setAlpha (alpha);
			concave.reconstruct(*cloud_hull);
			concave.reconstruct(*cloud_hull, polygons);
		}
		else //if(hulltype.compare("cv") == 0)
		{
			convex.setInputCloud (cloud);
			convex.reconstruct(*cloud_hull);
			convex.reconstruct(*cloud_hull, polygons);
		}

		std::cerr << "Mesh has: " << cloud_hull->points.size() << " data points." << std::endl;
		WritePCDFile(output_filename_, *cloud_hull, index);

		std::cerr << "polygon has: " << polygons.size() << " data points." << std::endl;
		WriteJSONFile(output_filename_, *cloud_hull,polygons, index);
	}

	return 0;
}