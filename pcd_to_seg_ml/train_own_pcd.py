'''
Refer to Open3D-ML/docs/tutorial/notebook/add_own_dataset.rst

In this tutorial, we will learn how to add a custom dataset that you can use to train a model. Before you add a custom dataset, ensure that you are familiar with the existing datasets in the scripts/download_datasets folder.
Before you start adding your own dataset to Open3D, ensure that you have copied the dataset to the folder <NTA>. We would also presume that you have decided on the model that you want to use for this custom dataset.
For this example, we will use an image dataset DogsAndCats.labels and the RandLANet model.

At a high-level, we will:
- Download and convert dataset
- Create the configuration file
- Read the dataset and use it train model for semantic segmentation


* Download and convert dataset

You must download the dataset to a folder and extract it. In this example, we are assuming you have extracted the dataset to the dataset\custom_dataset folder.
You must next preprocess the dataset to convert the labels to pointcloud.

    # Convert labels to pointcloud data
    cd dataset/custom_dataset
    python preprocess.py

* Create a configuration file

Your configuration file (randlanet_custom.yml) should include all information required to train a model using the custom dataset. To do this, your configuration file should include:
- dataset information
- model information
- pipeline information

'''
import torch
import open3d.ml.torch as ml3d
from open3d.ml.torch.models import RandLANet
from open3d.ml.torch.pipelines import SemanticSegmentation

'''
You can also create a custom dataset code and add it to `ml3d/datasets`. A Dataset class is independent of an ML framework and has to be derived from
`BaseDataset` defined in `ml3d/datasets/base_dataset.py`. You must implement another class `MyDatasetSplit` which is used to return data and attributes for files corresponding to a particular split.
'''
from open3d._ml3d.datasets.base_dataset import BaseDataset

class MyDataset(BaseDataset):
    def __init__(self, name="MyDataset"):
        super().__init__(name=name)
        # read file lists.

    def get_split(self, split):
        return MyDatasetSplit(self, split=split)

    def is_tested(self, attr):
        # checks whether attr['name'] is already tested.
        pass

    def save_test_result(self, results, attr):
        # save results['predict_labels'] to file.
        pass

class MyDatasetSplit():
    def __init__(self, dataset, split='train'):
        self.split = split
        self.path_list = []
        # collect list of files relevant to split.

    def __len__(self):
        return len(self.path_list)

    def get_data(self, idx):
        path = self.path_list[idx]
        points, features, labels = read_pcd(path)
        return {'point': points, 'feat': features, 'label': labels}

    def get_attr(self, idx):
        path = self.path_list[idx]
        name = path.split('/')[-1]
        return {'name': name, 'path': path, 'split': self.split}

def visualize():
    #Read a dataset by specifying the path. We are also providing the cache directory and training split.
    dataset = ml3d.datasets.Custom3DSplit(dataset_path='./dataset/custom_dataset', cache_dir='./logs/cache',training_split=['00', '01', '02', '03', '04', '05', '06', '07', '09', '10'])
    #Split the dataset for 'training'. You can get the other splits by passing 'validation' or 'test'
    train_split = dataset.get_split('training')

    #view the first 1000 frames using the visualizer
    vis = ml3d.vis.Visualizer()
    vis.visualize_dataset(dataset, 'training',indices=range(100))
    
def train():
    #Read a dataset by specifying the path. We are also providing the cache directory and training split.
    dataset = ml3d.datasets.custom_dataset(dataset_path='./dataset/custom_dataset', cache_dir='./logs/cache',training_split=['00', '01', '02', '03', '04', '05', '06', '07', '09', '10'])

    #Initialize the RandLANet model with three layers.
    model = RandLANet(dim_input=3)
    pipeline = SemanticSegmentation(model=model, dataset=dataset, max_epoch=100)

    #Run the training
    pipeline.run_train()    
    
if __name__ == '__main__':
    train()
    