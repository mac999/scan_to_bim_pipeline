# project 
Scan to BIM pipieline 

# description
Scan to BIM project has purpose like below. 

1. 3D point cloud processsing pipeline implementation dynamically using JSON.
2. Classification of outdoor building objects such as wall (facade), road etc. 
3. Extraction geometry information from classification.
4. Binding BIM object with geometry information and property set.

<img height="200" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept1.JPG"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/concept2.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/ifc_building_facade.jpg"/></BR><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_scan.JPG"/><img height="150" src="https://github.com/mac999/scan_to_bim_pipeline/blob/main/doc/indoor_BIM.PNG"/>

# version history
0.1: scan to bim framework released.

# installation 
This pipeline used geometry computation algorithms, deep learning etc. 

1. git clone https://github.com/mac999/scan_to_bim_pipeline
2. install python, pip
3. install gdal, pdal
4. install cuda, tensorflow, pytorch
5. pip -r install requirements.txt

# license
MIT license

# developed by 
KICT, IUPUI / Pudue / UNF univesity

# reference
Kang, T., Patil, S., Kang, K., Koo, D. and Kim, J., 2020. Rule-based scan-to-BIM mapping pipeline in the plumbing system. Applied Sciences, 10(21), p.7422. https://www.mdpi.com/2076-3417/10/21/7422

