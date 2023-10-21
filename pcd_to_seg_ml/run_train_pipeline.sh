# to fix error 'Weight tensor should be defined either for all or no classes' due to 2D weights, modify the below code considering Open3D-ML #601 issue
# nano .../ml3d/datasets/utils/dataprocessing.py
#      replace np.expand_dims(ce_label_weight, axis=0) to ce_label_weight. 
python scripts/run_pipeline.py torch -c ml3d/configs/randlanet_s3dis.yml --daaset.dataset_path /media/data/S3DIS/Standford3dDataset_v1.2 --device gpu --pipeline SemanticSegmentation --dataset.use_cache True