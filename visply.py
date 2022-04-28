import numpy as np
import open3d as o3d    

def main():
    cloud = o3d.io.read_point_cloud("./fuzzing/objects/1.ply") # Read the point cloud
    # cloud = o3d.io.read_point_cloud("./result/bench1/badlidar_v2.ply") # Read the point cloud
    o3d.visualization.draw_geometries([cloud]) # Visualize the point cloud     

if __name__ == "__main__":
    main()