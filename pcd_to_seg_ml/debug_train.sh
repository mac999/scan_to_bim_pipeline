# to fix error 'Weight tensor should be defined either for all or no classes' due to 2D weights, modify the below code considering Open3D-ML #601 issue
# nano /opt/conda/lib/python3.7/site-packages/open3d/_ml3d/datasets/utils/dataprocessing.py
#      replace np.expand_dims(ce_label_weight, axis=0) to ce_label_weight. 
python -m pdb ./train_pcd_on_torch.py