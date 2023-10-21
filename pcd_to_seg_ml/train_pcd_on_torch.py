# Train a Semantic Segmentation Model Using PyTorch
'''
- Read a dataset and get a training split. For this example, we will use SemanticKITTI dataset.
- Run a pre-trained model. For this example, we will use the RandLANet model.
- Train a model. We will train a model using the SemanticKITTI dataset and RandLANet model.
- Run an inference and run a test. We will run an inference using the 'training' split that use a pointcloud and display a result. However, a test is run on a pre-defined test set rather than a pass pointcloud.
'''
#Import torch and the model to use for training
import pdb
import open3d.ml as _ml3d
import open3d.ml.torch as ml3d
from open3d.ml.torch.models import RandLANet
from open3d.ml.torch.pipelines import SemanticSegmentation

def visualize():
    #Read a dataset by specifying the path. We are also providing the cache directory and training split.
    dataset = ml3d.datasets.S3DIS(dataset_path='./dataset/Stanford3dDataset_v1.2_Aligned_Version/', cache_dir='./logs/cache',training_split=['00', '01', '02', '03', '04', '05', '06', '07', '09', '10'])
    #Split the dataset for 'training'. You can get the other splits by passing 'validation' or 'test'
    train_split = dataset.get_split('training')

    #view the first 1000 frames using the visualizer
    vis = ml3d.vis.Visualizer()
    vis.visualize_dataset(dataset, 'training',indices=range(100))
    
def train():
    #Read a dataset by specifying the path. We are also providing the cache directory and training split.
    pdb.set_trace()
    cfg_file = "./configs/randlanet_s3dis.yml"
    cfg = _ml3d.utils.Config.load_from_file(cfg_file)

    #Initialize the RandLANet model with three layers.
    model = ml3d.models.RandLANet(**cfg.model)
    cfg.dataset['dataset_path'] = './dataset/Stanford3dDataset_v1.2_Aligned_Version_normal/'
    
    # dataset = ml3d.datasets.S3DIS(dataset_path='./dataset/Stanford3dDataset_v1.2_Aligned_Version/', cache_dir='./logs/cache',training_split=['00', '01', '02', '03', '04', '05', '06', '07', '09', '10'])
    dataset = ml3d.datasets.S3DIS(cfg.dataset.pop('dataset_path', None), **cfg.dataset)
    pipeline = ml3d.pipelines.SemanticSegmentation(model=model, dataset=dataset, device='gpu', **cfg.pipeline)

    # load pretrain
    # ckpt_path = "./logs/randlanet_s3dis_202010091238.pth"
    # pipeline.load_ckpt(ckpt_path=ckpt_path)

    #Run the training
    pipeline.run_train()    

'''
def inference():
    #Get pipeline, model, and dataset.
    Pipeline = get_module("pipeline", "SemanticSegmentation", "torch")
    Model = get_module("model", "RandLANet", "torch")
    Dataset = get_module("dataset", "SemanticKITTI")

    #Create a checkpoint
    RandLANet = Model(ckpt_path=args.path_ckpt_randlanet)
    SemanticKITTI = Dataset(args.path_semantickitti, use_cache=False)
    pipeline = Pipeline(model=RandLANet, dataset=SemanticKITTI)

    #Get data from the SemanticKITTI dataset using the "train" split
    train_split = SemanticKITTI.get_split("train")
    data = train_split.get_data(0)

    #Run the inference
    results = pipeline.run_inference(data)

    #Print the results
    print(results)    
    
def test():
    #Get pipeline, model, and dataset.
    Pipeline = get_module("pipeline", "SemanticSegmentation", "torch")
    Model = get_module("model", "RandLANet", "torch")
    Dataset = get_module("dataset", "SemanticKITTI")

    #Create a checkpoint
    RandLANet = Model(ckpt_path=args.path_ckpt_randlanet)
    SemanticKITTI = Dataset(args.path_semantickitti, use_cache=False)
    pipeline = Pipeline(model=RandLANet, dataset=SemanticKITTI)

    #Get data from the SemanticKITTI dataset using the "train" split
    train_split = SemanticKITTI.get_split("train")
    data = train_split.get_data(0)

    #Run the test
    pipeline.run_test(data)
'''

def main():
    train()
    
if __name__ == "__main__":
    main()
