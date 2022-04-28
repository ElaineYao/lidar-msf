import cv2
import numpy as np
 
 #(416, 416, 3)
img = cv2.imread('./data/cam.png', cv2.IMREAD_UNCHANGED)
 
print('Original Dimensions : ',img.shape)

inp_dim = (416, 416)
img_w, img_h = img.shape[1], img.shape[0]
w, h = inp_dim
new_w = int(img_w * min(w/img_w, h/img_h))
new_h = int(img_h * min(w/img_w, h/img_h))
resized_image = cv2.resize(img, (new_w,new_h), interpolation = cv2.INTER_CUBIC)
    
canvas = np.full((inp_dim[0], inp_dim[1], 3), 128)

canvas[(h-new_h)//2:(h-new_h)//2 + new_h,(w-new_w)//2:(w-new_w)//2 + new_w,  :] = resized_image




# resized_image = cv2.resize(img, (416, 416), interpolation = cv2.INTER_CUBIC)

print('Current Dimensions : ', canvas.shape)

# img = cv2.imread("./final_img_ori.jpg")
cv2.imwrite("./final_img_ori.jpg", canvas)