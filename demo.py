# import required libraries
import torch
import torchvision.transforms as T
from PIL import Image
import cv2
import numpy as np

# # define a torch tensor
# tensor = torch.rand(3,300,700)

# # define a transform to convert a tensor to PIL image
# transform = T.ToPILImage()
# print(tensor.size())
# # convert the tensor to PIL image using above transform
# img = transform(tensor)

# # display the PIL image
# img.show()

def load_bg(path, h=416, w=416):
    background = cv2.imread(path)
    background = cv2.resize(background, (h, w))
    # background = background[:, :, ::-1] / 255.0
    # background = background.astype(np.float32)
    cv2.imwrite('new.jpg', background)

if __name__ == '__main__':
    path = "./data/cam.png"
    load_bg(path)