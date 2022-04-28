import cv2
import numpy as np
from yaml import load
def load_bg(path, h=416, w=416):
        img = cv2.imread(path)
        # background = cv2.resize(background, (h, w))
        # background = background[:, :, ::-1] / 255.0

        inp_dim = (416, 416)
        img_w, img_h = img.shape[1], img.shape[0]
        print(img_w, img_h)
        w, h = inp_dim
        new_w = int(img_w * min(w/img_w, h/img_h))
        new_h = int(img_h * min(w/img_w, h/img_h))
        print(new_w, new_h)
        resized_image = cv2.resize(img, (new_w,new_h), interpolation = cv2.INTER_CUBIC)

        # impath = "./fuzzing/background/1.png"
        # img = cv2.imread(impath, 0)
        canvas = np.full((inp_dim[0], inp_dim[1], 3), 128)

        canvas[(h-new_h)//2:(h-new_h)//2 + new_h,(w-new_w)//2:(w-new_w)//2 + new_w,  :] = resized_image
        cv2.imwrite('new.jpg', canvas)
        # canvas = canvas[:, :, ::-1] / 255.0

        # self.background = canvas.astype(np.float32)

if __name__ == '__main__':
    path = "./fuzzing/background/4.png"
    load_bg(path)

