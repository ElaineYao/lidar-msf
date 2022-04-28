import cv2

path = "./blank.png"
img = cv2.imread(path)
        # background = cv2.resize(background, (h, w))
        # background = background[:, :, ::-1] / 255.0

inp_dim = (1242, 375)
img_w, img_h = img.shape[1], img.shape[0]
print(img_w, img_h) # 1242 375

resized_image = cv2.resize(img, inp_dim, interpolation = cv2.INTER_CUBIC)
filename = 'savedImage.jpg'
cv2.imwrite(filename, resized_image)