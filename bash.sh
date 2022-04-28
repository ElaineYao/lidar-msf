#!/bin/sh
# bench1
# python ./rendered_img_bench1.py -obj ./result/bench1/b3.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/cam.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 

# orignal bench
# python ./rendered_img_bench1.py -obj ./result/ori_bench/object.ply -obj_save ./result/ori_bench/bad -lidar ./data/lidar.bin -cam ./data/cam.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000

# blank background - bench1
# python ./rendered_img_bench1.py -obj ./result/bench1/b3.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/blank.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 

# blank background - ori bench
# python ./rendered_img_bench1.py -obj ./result/ori_bench/object.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/blank.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 

# generate adversarial objects
python ./attack_bench1.py -obj ./fuzzing/objects/1.ply -obj_save ./result/bench1/bad -lidar ./fuzzing/background/2.bin -cam ./fuzzing/background/2.png -cali ./fuzzing/background/2.txt -e 0.2 -o pgd -it 400 

# adversarial objects
# python ./rendered_img_bench1.py -obj ./result/bench1/badlidar_v2.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/blank.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 

# ori background - chair
# python ./rendered_img_bench1.py -obj ./fuzzing/objects/b3_ssss5.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/cam.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 

# blank background - ori bench
# python ./rendered_img_bench1.py -obj ./fuzzing/objects/2.ply -obj_save ./result/bench1/bad -lidar ./data/lidar.bin -cam ./data/cam.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 