import time
from subprocess import *
import os
import random

NUM_ITERATION = 2
X_MIN = 40
X_MAX = 85
Y_MIN = -8
Y_MAX = 8
R_MIN = 0.1
R_MAX = 0.2

object = "./fuzzing/objects/1.ply"
lidar = "./fuzzing/background/1.bin"
cali = "./fuzzing/background/1.txt"
bg = "./fuzzing/background/1.png"
x = 5
y = 7
r = 0.2

# python attack.py -obj ./object/object.ply -obj_save ./object/obj_save -lidar
#  ./data/lidar.bin -cam ./data/cam.png -cali ./data/cali.txt -e 0.2 -o pgd -it 1000 
# -x 5 -y 7 -r 0.2

# c = 'gnome-terminal -- python ./test_attack.py -obj '+ str(object)+' -obj_save ./object/obj_save -lidar '+str(lidar)+' -cam '+str(bg)+' -cali '+str(cali)+' -e 0.2 -o pgd -it 1000 -x '+str(x)+' -y '+str(y)+' -r '+str(r)
# # print(c)
# handle = Popen(c, stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)

while(True):
    # time.sleep(10)

    # f = open("restart.txt", "r")

    # if the previous program has finished
    # if f.read() == "restart":
        # f.close()
        # open("restart.txt", "w").close()
    # Choose bg
    n = random.randint(1,4)
    # Choose object
    m = random.randint(1,3)
    object = "./fuzzing/objects/"+str(m)+".ply"
    lidar = "./fuzzing/background/"+str(n)+".bin"
    cali = "./fuzzing/background/"+str(n)+".txt"
    bg = "./fuzzing/background/"+str(n)+".png"
    # Choose x, y, r
    x = random.uniform(X_MIN, X_MAX)
    y = random.uniform(Y_MIN, Y_MAX)
    r = random.uniform(R_MIN, R_MAX)
    c = 'gnome-terminal -- python ./attack_bench1.py -obj '+ str(object)+' -obj_save ./object/obj_save -lidar '+str(lidar)+' -cam '+str(bg)+' -cali '+str(cali)+' -e 0.2 -o pgd -it 400 -x '+str(x)+' -y '+str(y)+' -r '+str(r)
    # print(c)
    fi = open("restart.txt", "a")
    fi.write(c+"\n")
    fi.close()
    handle = Popen(c, stdin=PIPE, stderr=PIPE, stdout=PIPE, shell=True)

    time.sleep(60*7.5)

