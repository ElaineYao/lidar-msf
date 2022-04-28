import argparse
import cv2


import argparse
import os

import cv2
import matplotlib.pyplot as plt
import neural_renderer as nr
import numpy as np
import torch
import torch.autograd as autograd
import torch.nn.functional as F
import torchvision
import torchvision.transforms as T
from PIL import Image
from plyfile import *
from scipy.spatial.transform import Rotation as R
from skimage.io import imread, imsave

import cluster
import loss_LiDAR
import render
from c2p_segmentation import *
from pytorch.renderer import nmr
from pytorch.yolo_models.darknet import Darknet
from pytorch.yolo_models.utils_yolo import *
from xyz2grid import *


def read_cali(path):
    file1 = open(path, 'r')
    Lines = file1.readlines()
    for line in Lines:
        if 'R:' in line:
            rotation = line.split('R:')[-1]
        if 'T:' in line:
            translation = line.split('T:')[-1]
    tmp_r = rotation.split(' ')
    tmp_r.pop(0)
    tmp_r[-1] = tmp_r[-1].split('\n')[0]
    rota_matrix = []

    for i in range(3):
        tt = []
        for j in range(3):
            tt.append(float(tmp_r[i * 3 + j]))
        rota_matrix.append(tt)
    rota_matrix = np.array(rota_matrix)
    tmp_t = translation.split(' ')
    tmp_t.pop(0)
    tmp_t[-1] = tmp_t[-1].split('\n')[0]
    trans_matrix = [float(tmp_t[i]) for i in range(3)]
    trans_matrix = np.array(trans_matrix)
    return rota_matrix, trans_matrix

def predict_convert(image_var, model, class_names, reverse=False):
    # pred = model.get_spec_layer( (image_var - mean_var ) / std_dv_var, 0).max(1)[1]
    pred, _ = model(image_var)
    # print(np.array(pred).shape)
    boxes = []
    img_vis = []
    pred_vis = []
    vis = []
    i = 0
    boxes.append(nms(pred[0][i] + pred[1][i] + pred[2][i], 0.4))
    img_vis.append((image_var[i].cpu().data.numpy().transpose(1, 2, 0) * 255).astype(np.uint8))

    pred_vis.append(plot_boxes(Image.fromarray(img_vis[i]), boxes[i], class_names=class_names))
    vis = np.array(pred_vis[i][0])
    return np.array(vis), np.array(boxes)

class attack_msf():
    def __init__(self, args):
        self.args = args
        self.num_pos = 1
        self.threshold = 0.4
        self.root_path = './data/'
        self.pclpath = 'pcd/'
        self.rotation = torch.tensor(np.array([[1., 0., 0.],
                                               [0., 0., -1.],
                                               [0., 1., 0.]]), dtype=torch.float)
        self.protofile = self.root_path + 'deploy.prototxt'
        self.weightfile = self.root_path + 'deploy.caffemodel'
        self.outputs = ['instance_pt', 'category_score', 'confidence_score',
                   'height_pt', 'heading_pt', 'class_score']
        self.esp = args.epsilon
        self.direction_val, self.dist_val = self.load_const_features('./data/features_1.out')

    def init_render(self, image_size = 416):
        self.image_size = image_size
        self.renderer = nr.Renderer(image_size=image_size, camera_mode='look_at',
                                    anti_aliasing=False, light_direction=(0, 0, 0), background_color=[255,255,255])
        exr = cv2.imread('./data/dog.exr', cv2.IMREAD_UNCHANGED)
        self.renderer.light_direction = [1, 3, 1]

        # set the light for
        ld, lc, ac = nmr.lighting_from_envmap(exr)
        self.renderer.light_direction = ld
        self.renderer.light_color = lc
        self.renderer.ambient_color = ac

    def load_const_features(self, fname):

        print("Loading dircetion, dist")
        features_filename = fname

        features = np.loadtxt(features_filename)
        features = np.swapaxes(features, 0, 1)
        features = np.reshape(features, (1, 512, 512, 8))

        direction = np.reshape(features[:, :, :, 3], (1, 512, 512, 1))
        dist = np.reshape(features[:, :, :, 6], (1, 512, 512, 1))
        return torch.tensor(direction).cuda().float(), torch.tensor(dist).cuda().float()

    def model_val_lidar(self, protofile, weightfile):
        net = CaffeNet(protofile, phase='TEST')
        # torch.cuda.set_device(0)
        net.cuda()
        net.load_weights(weightfile)
        net.set_train_outputs(outputs)
        net.set_eval_outputs(outputs)
        net.eval()
        for p in net.parameters():
            p.requires_grad = False
        return net

    def load_LiDAR_model(self, ):
        self.LiDAR_model = generatePytorch(self.protofile, self.weightfile).cuda()
        self.LiDAR_model_val = self.model_val_lidar(self.protofile, self.weightfile)

    def load_model_(self):

        namesfile = './pytorch/yolo_models/data_yolo/coco.names'
        class_names = load_class_names(namesfile)
        single_model = Darknet('./pytorch/yolo_models/cfg/yolov3.cfg')
        single_model.load_weights('./data/yolov3.weights')
        model = single_model
        self.model = model.cuda()
        self.model.eval()

    def load_pc_mesh(self, path):
        PCL_path = path

        # loading ray_direction and distance for the background pcd
        self.PCL = loadPCL(PCL_path, True)
        x_final = torch.FloatTensor(self.PCL[:, 0]).cuda()
        y_final = torch.FloatTensor(self.PCL[:, 1]).cuda()
        z_final = torch.FloatTensor(self.PCL[:, 2]).cuda()
        self.i_final = torch.FloatTensor(self.PCL[:, 3]).cuda()
        self.ray_direction, self.length = render.get_ray(x_final, y_final, z_final)


    # x_of=7
    def load_mesh(self, path, r, x_of=87, y_of=5):
        # z_of = -1.73 + r / 2.
        z_of = -15 + r / 2.
        plydata = PlyData.read(path)
        # r is scaling factor controlling the size of the 3d object
        x = torch.FloatTensor(plydata['vertex']['x']) * r
        y = torch.FloatTensor(plydata['vertex']['y']) * r
        z = torch.FloatTensor(plydata['vertex']['z']) * r
        self.object_v = torch.stack([x, y, z], dim=1).cuda()

        self.object_f = plydata['face'].data['vertex_indices']
        self.object_f = torch.tensor(np.vstack(self.object_f)).cuda()

        rotation = lidar_rotation.cuda()
        self.object_v = self.object_v.cuda()
        self.object_v = self.object_v.permute(1, 0)
        self.object_v = torch.matmul(rotation, self.object_v)
        self.object_v = self.object_v.permute(1, 0)
        # x_of controls the x-axis movement 
        self.object_v[:, 0] += x_of
        self.object_v[:, 1] += y_of
        self.object_v[:, 2] += z_of

        self.object_ori = self.object_v.clone()

        camera_v = self.object_v.clone()
        camera_v = camera_v.permute(1, 0)
        r, t = torch.tensor(self.rota_matrix).cuda().float(), torch.tensor(self.trans_matrix).cuda().float()
        r_c = R.from_euler('zxy', [0, 180, 180], degrees=True)
        camera_rotation = torch.tensor(r_c.as_matrix(), dtype=torch.float).cuda()
        camera_v = torch.matmul(camera_rotation, camera_v)
        camera_v = torch.matmul(r, camera_v)
        camera_v = camera_v.permute(1, 0)

        camera_v += t

        c_v_c = camera_v.cuda()

        self.vn, idxs = self.set_neighbor_graph(self.object_f, c_v_c)
        self.vn_tensor = torch.Tensor(self.vn).view(-1).cuda().long()
        self.idxs_tensor = torch.Tensor(idxs.copy()).cuda().long()

        self.object_t = torch.tensor(self.object_v.new_ones(self.object_f.shape[0], 1, 1, 1, 3)).cuda()
        # color grey
        # self.object_t[:, :, :, :, 1] = 0.3
        # self.object_t[:, :, :, :, 2] = 0.3
        # self.object_t[:, :, :, :, 0] = 0.3
        # wood brown rgb: (164,116,73)
        self.object_t[:, :, :, :, 0] = 164/255
        self.object_t[:, :, :, :, 1] = 116.3/255
        self.object_t[:, :, :, :, 2] = 73.3/255
        # lemonade rgb: (253, 185, 200)
        # self.object_t[:, :, :, :, 0] = 253/255
        # self.object_t[:, :, :, :, 1] = 185/255
        # self.object_t[:, :, :, :, 2] = 200/255
        self.mean_gt = self.object_ori.mean(0).data.cpu().clone().numpy()


    def set_learning_rate(self, optimizer, learning_rate):
        for param_group in optimizer.param_groups:
            param_group['lr'] = learning_rate

    def tv_loss_(self, image, ori_image):
        noise = image - ori_image
        loss = torch.mean(torch.abs(noise[:, :, :, :-1] - noise[:, :, :, 1:])) + torch.mean(
            torch.abs(noise[:, :, :-1, :] - noise[:, :, 1:, :]))
        return loss

    def load_bg(self, path, h=416, w=416):
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
    
        canvas = np.full((inp_dim[0], inp_dim[1], 3), 128)

        canvas[(h-new_h)//2:(h-new_h)//2 + new_h,(w-new_w)//2:(w-new_w)//2 + new_w,  :] = resized_image
        canvas = canvas[:, :, ::-1] / 255.0

        self.background = canvas.astype(np.float32)

    def compute_total_variation_loss(self, img1, img2):
        diff = img1 - img2
        tv_h = ((diff[:,:,1:,:] - diff[:,:,:-1,:]).pow(2)).sum()
        tv_w = ((diff[:,1:,:,:] - diff[:,:-1,:,:]).pow(2)).sum()
        return tv_h + tv_w

    def l2_loss(self, desk_t, desk_v, ori_desk_t, ori_desk_v):
        t_loss = torch.nn.functional.mse_loss(desk_t, ori_desk_t)
        v_loss = torch.nn.functional.mse_loss(desk_v, ori_desk_v)
        return v_loss, t_loss

    def rendering_img(self, ppath):
        u_offset = 0
        v_offset = 0

        lr = 0.005
        best_it = 1e10
        num_class = 80
        threshold = 0.5
        batch_size = 1

        self.object_v.requires_grad = True
        # bx is the original object, first we add random noise to object vertex to start with
        bx = self.object_v.clone().detach().requires_grad_()
        sample_diff = np.random.uniform(-0.001, 0.001, self.object_v.shape)
        sample_diff = torch.tensor(sample_diff).cuda().float()
        sample_diff.clamp_(-args.epsilon, args.epsilon)
        self.object_v.data = sample_diff + bx
        iteration = self.args.iteration
        
        camera_v = bx.clone()
        # camera_v = self.object_v.clone()
        # print()
        camera_v = camera_v.permute(1, 0)

        r, t = torch.tensor(self.rota_matrix).cuda().float(), torch.tensor(self.trans_matrix).cuda().float()
        r_c = R.from_euler('zxy', [0, 180, 180], degrees=True)
        camera_v = torch.matmul(r, camera_v)
        camera_v = camera_v.permute(1, 0)
        camera_v = camera_v.permute(1, 0)
        camera_rotation = torch.tensor(r_c.as_matrix(), dtype=torch.float).cuda()
        camera_v = torch.matmul(camera_rotation, camera_v)
        camera_v = camera_v.permute(1, 0)
        camera_v += t

        # Dose camera_v mean the rotated object vertex?
        c_v_c = camera_v.cuda()
    
        # unsqueeze(0) add a dimension in x , e.g. (4) ->(1,4)
        # vertex, face, texture
        # image_tensor is the image of 3d object. The location is the same as final image. 
        # The goal of rendering is 
        # torch.Size([1, 3, 416, 416])
        image_tensor = self.renderer.render(c_v_c.unsqueeze(0), self.object_f.unsqueeze(0), self.object_t.unsqueeze(0))[0].cuda() 
        # print("image_tensor rgb: ")
        # temp1 = image_tensor[0, :, 1, 1] # rgb value of image_tensor
        # temp1 = image_tensor[:,0,:, :]
        # temp2 = temp1[temp1<255] # tensor([0.2347, 0.2390, 0.2875,  ..., 0.2215, 0.1500, 0.1500]
        # print(temp2)
        # print(image_tensor[0, 0, 1, 1])
        # print(image_tensor[0, 1, 1, 1])
        # print(image_tensor[0, 2, 1, 1])

        # tmp1 = image_tensor.detach().cpu().numpy() #len(tmp1) = 1
        # tmp2 = tmp1[0] # <class 'numpy.ndarray'> #len(tmp2) =2
        # print("tmp: ")
        # print(len(tmp1))
        # print(len(tmp2))
        image = image_tensor.detach().cpu().numpy()[0].transpose((1, 2, 0))
        # print("image: ")
        # print(image.shape())
        imsave('image_3d.png', image)
        # silhouettes: the dark shape and outline of someone visible against a lighter background -> this is to cut the image
        mask_tensor = self.renderer.render_silhouettes(c_v_c.unsqueeze(0), self.object_f.unsqueeze(0)).cuda()
        # background tensor. from_numpy -> create a tensor from numpy
        background_tensor = torch.from_numpy(self.background.transpose(2, 0, 1)).cuda() # torch.Size([3, 416, 416]) range [0, 1]
        # print("background_tensor:")
        # min_1 = 300
        # max_1 = -300
        # min_1 = 300
        # max_1 = -300
        # min_1 = 300
        # max_1 = -300
        # for i in range(416):
        #     for j in range(416):
        #         r = background_tensor[0, i, j]
        #         g = background_tensor[1, i, j]
        #         b = background_tensor[2, i, j]
        #         if(r>max_1):
        #             max_1 = r
        #         elif(r<min_1):
        #             min_1 = r
        #         if(g>max_1):
        #             max_1 = g
        #         elif(g<min_1):
        #             min_1 = g
        #         if(b>max_1):
        #             max_1 = b
        #         elif(b<min_1):
        #             min_1 = b
        # print("min = "+str(min_1)+", max = "+str(max_1))

        # create an empty tensor with the same size as background_tensor
        fg_mask_tensor = torch.zeros(background_tensor.size())
        # repeat: repeat this tensor along the specified dimensions
        # repeat(size), size: number of times to repeat this tensor along each dimension
        new_mask_tensor = mask_tensor.repeat(3, 1, 1)
        # Not sure?
        fg_mask_tensor[:, u_offset: u_offset + self.image_size,
        v_offset: v_offset + self.image_size] = new_mask_tensor
        fg_mask_tensor = fg_mask_tensor.byte().cuda()
        new_mask_tensor = new_mask_tensor.byte().cuda()
        # masked(mask, source); mask-> boolean mask; source(Tensor)-> the tensor to copy from
        # Copies elements from source into self tensor at positions where the mask is True. The shape of mask must be broadcastable with the shape of the underlying tensor. 
        # The source should have at least as many elements as the number of ones in mask
        # mask controls the insertion place while 
        # masked_select(): cut the image_tensor according to mask 
        background_tensor.masked_scatter_(fg_mask_tensor, image_tensor.masked_select(new_mask_tensor)) # torch.Size([3, 416, 416])
        # img_ = torch.squeeze(background_tensor)
        # transform = T.ToPILImage()
        # img_ = img_.detach().cpu()
        # # convert the tensor to PIL image using above transform
        # img = transform(img_)
        # # display the PIL image
        # img.save("./result/bench1/benign.jpg") 
        # image = background_tensor.detach().cpu().numpy()[0].transpose((1, 2, 0))
        # restrict the image value to be between [0,1], truncate the larger/smaller value
        final_image = torch.clamp(background_tensor.float(), 0, 1)[None]   #([1,3,416,416])
        # print("final_image shape: ")
        # print(final_image.size())
        image = final_image.detach().cpu().numpy()[0].transpose((1, 2, 0))
        imsave('./fuzzing/result/'+str(args.x)+'.jpg', image)
        # img_ = torch.squeeze(final_image)
        # transform = T.ToPILImage()
        # img_ = img_.detach().cpu()
        # # convert the tensor to PIL image using above transform
        # img = transform(img_)
        # # display the PIL image
        # img.save("./result/bench1/benign.jpg") 


        # for it in range(iteration):

        #     if it % 200 == 0:
        #         lr = lr / 10.0
        #     l_c_c_ori = self.object_ori
        #     self.object_f = self.object_f.cuda()
        #     self.i_final = self.i_final.cuda()

        #     self.object_v = self.object_v.cuda()
        #     # self.object_v = self.random_obj(self.object_v)
        #     adv_total_loss = None

        #     point_cloud = render.render(self.ray_direction, self.length, self.object_v, self.object_f, self.i_final)
        #     # print("-----")
        #     # print("#######")
        #     # print(point_cloud.size())
        #     grid = xyzi2grid_v2(point_cloud[:, 0], point_cloud[:, 1], point_cloud[:, 2], point_cloud[:, 3])

        #     featureM = gridi2feature_v2(grid, self.direction_val, self.dist_val)

        #     outputPytorch = self.LiDAR_model(featureM)
            # print("-----")
            # print("#######")
            # cate = outputPytorch[5].detach()
            # cat = np.squeeze(cate)
            # cat = cat[2,:,:]
            # plt.imshow(cat,cmap='gray')
            # plt.savefig('height3.png')
            # img_ = torch.squeeze(outputPytorch[0])
            # transform = T.ToPILImage()
            # print(img_.size())
            # img_ = img_.detach().cpu()
            # convert the tensor to PIL image using above transform
            # img = transform(img_)
            # i = 0
            # display the PIL image
            # img.save("category.jpg")
            # print(outputPytorch[5].size())
            # print(len(outputPytorch))
            # print("-----")
        #     lossValue, loss_object, loss_distance, loss_center, loss_z = loss_LiDAR.lossRenderAttack(outputPytorch, self.object_v, self.object_ori, self.object_f, 0.05)

        #     camera_v = self.object_v.clone()
        #     camera_v = camera_v.permute(1, 0)

        #     r, t = torch.tensor(self.rota_matrix).cuda().float(), torch.tensor(self.trans_matrix).cuda().float()
        #     r_c = R.from_euler('zxy', [0, 180, 180], degrees=True)
        #     camera_v = torch.matmul(r, camera_v)
        #     camera_v = camera_v.permute(1, 0)
        #     camera_v = camera_v.permute(1, 0)
        #     camera_rotation = torch.tensor(r_c.as_matrix(), dtype=torch.float).cuda()
        #     camera_v = torch.matmul(camera_rotation, camera_v)
        #     camera_v = camera_v.permute(1, 0)
        #     camera_v += t

        #     c_v_c = camera_v.cuda()
        #     image_tensor = self.renderer.render(c_v_c.unsqueeze(0), self.object_f.unsqueeze(0), self.object_t.unsqueeze(0))[0].cuda()
        #     mask_tensor = self.renderer.render_silhouettes(c_v_c.unsqueeze(0), self.object_f.unsqueeze(0)).cuda()
        #     background_tensor = torch.from_numpy(self.background.transpose(2, 0, 1)).cuda()
        #     fg_mask_tensor = torch.zeros(background_tensor.size())
        #     new_mask_tensor = mask_tensor.repeat(3, 1, 1)
        #     fg_mask_tensor[:, u_offset: u_offset + self.image_size,
        #     v_offset: v_offset + self.image_size] = new_mask_tensor
        #     fg_mask_tensor = fg_mask_tensor.byte().cuda()
        #     new_mask_tensor = new_mask_tensor.byte().cuda()

        #     background_tensor.masked_scatter_(fg_mask_tensor, image_tensor.masked_select(new_mask_tensor))

        #     final_image = torch.clamp(background_tensor.float(), 0, 1)[None]
        #     final, outputs = self.model(final_image)

        #     num_pred = 0.0
        #     removed = 0.0
        #     for index, out in enumerate(outputs):
        #         num_anchor = out.shape[1] // (num_class + 5)
        #         # shape the tensor
        #         out = out.view(batch_size * num_anchor, num_class + 5, out.shape[2], out.shape[3])
        #         cfs = torch.nn.functional.sigmoid(out[:, 4]).cuda()
        #         mask = (cfs >= threshold).type(torch.FloatTensor).cuda()
        #         num_pred += torch.numel(cfs)
        #         removed += torch.sum((cfs < threshold).type(torch.FloatTensor)).data.cpu().numpy()

        #         loss = torch.sum(mask * ((cfs - 0) ** 2 - (1 - cfs) ** 2))

        #         if adv_total_loss is None:
        #             adv_total_loss = loss
        #         else:
        #             adv_total_loss += loss
        #     total_loss = 12 * (F.relu(torch.clamp(adv_total_loss, min=0) - 0.01) / 5.0)
        #     # total_loss is the overall loss function
        #     total_loss += lossValue
        #     # best_it is the min total_loss,meaning, best stores the best result
        #     if best_it > total_loss.data.cpu() or it == 0:
        #         best_it = total_loss.data.cpu().clone()
        #         best_vertex = self.object_v.data.cpu().clone()
        #         best_final_img = final_image.data.cpu().clone()
        #         best_out = outputs.copy()
        #         best_face = self.object_f.data.cpu().clone()
        #         best_out_lidar = outputPytorch[:]
        #         pc_ = point_cloud[:, :3].cpu().detach().numpy()

        #     # print('Iteration {} of {}: Loss={}'.format(it, iteration, total_loss.data.cpu().numpy()))
        #     self.object_v = self.object_v.cuda()

        #     if self.args.opt == "Adam":
        #         # clears old gradients from the last step
        #         opt.zero_grad()
        #         # computes the derivative of the loss w.r.t. the parameters using backpropagation.
        #         total_loss.backward(retain_graph=True)
        #         # causes the optimizer to take a step based on the gradients of the parameters.
        #         opt.step()
        #     else:
        #         # defaul is pgd optimization
        #         pgd_grad = autograd.grad([total_loss.sum()], [self.object_v])[0]
        #         with torch.no_grad():
        #             loss_grad_sign = pgd_grad.sign()
        #             self.object_v.data.add_(-lr, loss_grad_sign)
        #             diff = self.object_v - bx
        #             diff.clamp_(-self.esp, self.esp)
        #             self.object_v.data = diff + bx
        #         del pgd_grad
        #         del diff

        #     if it < iteration - 1:
        #         del total_loss
        #         del featureM
        #         del grid
        #         del point_cloud

        # print('best iter: {}'.format(best_it))
        # diff = self.object_v - bx
        # vertice = best_vertex.numpy()
        # face = best_face.numpy()
        # pp = ppath.split('/')[-1].split('.bin')[0]
        # # through vertex and face we can reconstruct this object
        # # to create a ply file, save other elements in ply and only change the vertex , tho I don't know what r is for
        # render.savemesh(self.args.object, self.args.object_save + pp + '_v2.ply', vertice, face, r=0.33)

        # # because plydata['vertex']['x'] = vertice[:, 0]
        # # x range:  0.7310238
        # # y range:  0.8536951
        # # z range:  1.2403252

        # print('x range: ', vertice[:, 0].max() - vertice[:, 0].min())
        # print('y range: ', vertice[:, 1].max() - vertice[:, 1].min())
        # print('z range: ', vertice[:, 2].max() - vertice[:, 2].min())
        # ######################
        # PCLConverted = mapPointToGrid(pc_)

        # print('------------  Pytorch Output ------------')
        # # len(obj) = 119, len(label_map) = (262144,)
        # obj, label_map = cluster.cluster(best_out_lidar[1].cpu().detach().numpy(), best_out_lidar[2].cpu().detach().numpy(), best_out_lidar[3].cpu().detach().numpy(), best_out_lidar[0].cpu().detach().numpy(), best_out_lidar[5].cpu().detach().numpy())
        # # print("obj len is: "+str(len(obj))+", label_map len is: "+str(label_map.shape))
        # # with open('obj.txt', 'w') as f:
        # #     for item in obj:
        # #         f.write("%s\n" % item)
        # # np.savetxt("label_map.txt", label_map, delimiter =", ")

        # # len(obstacle) = 17, obstacle object; len(cluster_id_list) = 119
        # obstacle, cluster_id_list = twod2threed(obj, label_map, self.PCL, PCLConverted)
        # # print("obstacle len is: "+str(len(obstacle))+", cluster_id_list: "+str(len(cluster_id_list)))
        # # with open('obstacle.txt', 'w') as f:
        # #     for item in obstacle:
        # #         f.write("%s\n" % item)
        # # with open('cluster_id_list.txt', 'w') as f:
        # #     for item in cluster_id_list:
        # #         f.write("%s\n" % item)

        # self.pc_save = pc_
        # print("*****")
        # print("size of pc_save is: "+str(type(self.pc_save)))
        # print("len of pc_save is: "+str(len(self.pc_save)))
        # self.best_final_img = best_final_img.numpy()
        # self.best_vertex = best_vertex.numpy()
        # self.benign = bx.clone().data.cpu().numpy()

        # # Elaine

        # cam_img = self.best_final_img.detach()
        # cat = np.squeeze(cam_img)
        # # cat = cat[2,:,:]
        # plt.imshow(cam_img)
        # plt.savefig('final_img.png')




        # img_ = torch.squeeze(final_image)
        #     transform = T.ToPILImage()
        #     # print(img_.size())
        #     img_ = img_.detach().cpu()
        #     # convert the tensor to PIL image using above transform
        #     img = transform(img_)
        #     i = 0
        #     # display the PIL image
        #     img.save("final_image"+str(i)+".jpg")
        #     i +=1
        #     # im = Image.fromarray(final_image)
        #     # im.save("final.jpg")
        #     final, outputs = self.model(final_image)



    def savemesh(self, path_r, path_w, vet, r):
        plydata = PlyData.read(path_r)
        plydata['vertex']['x'] = vet[:, 0] / r
        plydata['vertex']['y'] = vet[:, 1] / r
        plydata['vertex']['z'] = vet[:, 2] / r

        plydata.write(path_w)
        return

    def set_neighbor_graph(self, f, vn, degree=1):
        max_len = 0
        face = f.cpu().data.numpy()
        vn = vn.data.cpu().tolist()
        for i in range(len(face)):
            # print((face[i]))
            v1, v2, v3 = face[i]
            for v in [v1, v2, v3]:
                vn[v].append(v2)
                vn[v].append(v3)
                vn[v].append(v1)

        # two degree
        for i in range(len(vn)):
            vn[i] = list(set(vn[i]))
        for de in range(degree - 1):
            vn2 = [[] for _ in range(len(vn))]
            for i in range(len(vn)):
                for item in vn[i]:
                    vn2[i].extend(vn[item])

            for i in range(len(vn2)):
                vn2[i] = list(set(vn2[i]))
            vn = vn2
        max_len = 0
        len_matrix = []
        for i in range(len(vn)):
            vn[i] = list(set(vn[i]))
            len_matrix.append(len(vn[i]))

        idxs = np.argsort(len_matrix)[::-1][:len(len_matrix) // 1]
        max_len = len_matrix[idxs[0]]
        print("max_len: ", max_len)

        vns = np.zeros((len(idxs), max_len))
        # for i in range( len(vn)):
        for i0, i in enumerate(idxs):
            for j in range(max_len):
                if j < len(vn[i]):
                    vns[i0, j] = vn[i][j]
                else:
                    vns[i0, j] = i
        return vns, idxs

    def read_cali(self, path):
        file1 = open(path, 'r')
        Lines = file1.readlines()
        for line in Lines:
            if 'R:' in line:
                rotation = line.split('R:')[-1]
            if 'T:' in line:
                translation = line.split('T:')[-1]
        tmp_r = rotation.split(' ')
        tmp_r.pop(0)
        tmp_r[-1] = tmp_r[-1].split('\n')[0]
        # print(tmp_r)
        rota_matrix = []

        for i in range(3):
            tt = []
            for j in range(3):
                tt.append(float(tmp_r[i * 3 + j]))
            rota_matrix.append(tt)
        self.rota_matrix = np.array(rota_matrix)
        tmp_t = translation.split(' ')
        tmp_t.pop(0)
        tmp_t[-1] = tmp_t[-1].split('\n')[0]
        # print(tmp_t)
        trans_matrix = [float(tmp_t[i]) for i in range(3)]
        self.trans_matrix = np.array(trans_matrix)


r = R.from_euler('zxy', [10,80,4], degrees=True)
lidar_rotation = torch.tensor(r.as_matrix(), dtype=torch.float).cuda()

if __name__ == '__main__':
    # open('restart.txt', 'w').close()
    parser = argparse.ArgumentParser()
    parser.add_argument('-obj', '--obj', dest='object', default="./object/object.ply") # 3d object
    parser.add_argument('-obj_save' ,'--obj_save', dest='object_save', default="./object/obj_save")
    parser.add_argument('-lidar', '--lidar', dest='lidar', default = "./data/lidar.bin") # corresponding lidar with bg
    parser.add_argument('-cam', '--cam', dest='cam', default="./data/cam.png") # background
    parser.add_argument('-cali', '--cali', dest='cali', default="./data/cali.txt") # corresponding cali with bg
    parser.add_argument('-o', '--opt', dest='opt', default="pgd")
    parser.add_argument('-e', '--epsilon', dest='epsilon', type=float, default=0.2)
    parser.add_argument('-it', '--iteration', dest='iteration', type=int, default=1000)
    # parser.add_argument('-it', '--iteration', dest='iteration', type=int, default=1000)
    parser.add_argument('-x', '--x', dest='x',default=7)
    parser.add_argument('-y', '--y', dest='y',default=0)
    parser.add_argument('-r', '--r', dest='r',default=0.15)

    args = parser.parse_args()

    print("-object: "+str(args.object))
    print("-object_save: "+str(args.object_save))
    print("-lidar: "+str(args.lidar))
    print("-args.x: "+str(args.x))

    obj = attack_msf(args)
    obj.load_model_()
    # obj.load_LiDAR_model()
    obj.read_cali(args.cali)
    obj.load_mesh(args.object, 0.2) #0.15
    obj.load_bg(args.cam)
    obj.init_render()
    obj.load_pc_mesh(args.lidar)
    obj.rendering_img(args.lidar)


    # fi = open("restart.txt", "w")
    # fi.write("restart")
    # fi.close()

    # impath = "./fuzzing/background/1.png"
    # img = cv2.imread(impath, 0)
    # cv2.imwrite('new'+str(args.x)+'.jpg', img)
    # we should add so that the terminal can continue running. Or we can 
    # while(1):
    #     i =1