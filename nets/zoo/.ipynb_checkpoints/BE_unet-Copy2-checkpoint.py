import torch
import torch.nn as nn
import skimage
import numpy as np
from torch.autograd import Variable
import torch.nn.functional as F


def double_conv(in_channels, out_channels):
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_channels, out_channels, 3, padding=1),
        nn.ReLU(inplace=True)
    )   

class _up_deconv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(_up_deconv, self).__init__()        
        
        self.deconv = nn.ConvTranspose2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=2, padding=1, output_padding=1)
        
        self.relu = nn.ReLU()
        
    def forward(self, x):
        
        out = self.deconv(x)
        out = self.relu(out)
        
        return out
    
class BE_unet(nn.Module):

    def __init__(self, n_class=1, pretrained=False):
        super().__init__()
        
        n_channels = 32
                

        self.dconv_down1 = double_conv(3, 64)
        self.dconv_down2 = double_conv(64, 128)
        self.dconv_down3 = double_conv(128, 256)
        self.dconv_down4 = double_conv(256, 512)        
        self.dconv_down5 = double_conv(512, 1024)
        self.maxpool = nn.MaxPool2d(2)                
        self.upsample5 = _up_deconv(1024,512)        
        self.upsample4 = _up_deconv(512,256)
        self.upsample3 = _up_deconv(256,128)
        self.upsample2 = _up_deconv(128,64)
        self.dconv_up4 = double_conv(512 + 512, 512)
        self.dconv_up3 = double_conv(256 + 256, 256)
        self.dconv_up2 = double_conv(128 + 128, 128)
        self.dconv_up1 = double_conv(64 + 64, 64)       
        
        # HED Block
#         self.dsn1 = nn.Conv2d(64, 1, 1)
#         self.dsn2 = nn.Conv2d(128, 1, 1)
#         self.dsn3 = nn.Conv2d(256, 1, 1)
#         self.dsn4 = nn.Conv2d(512, 1, 1)
#         self.dsn5 = nn.Conv2d(1024, 1, 1)
        # softmax ver
        self.dsn1 = nn.Conv2d(64, 2, 1)
        self.dsn2 = nn.Conv2d(128, 2, 1)
        self.dsn3 = nn.Conv2d(256, 2, 1)
        self.dsn4 = nn.Conv2d(512, 2, 1)
        self.dsn5 = nn.Conv2d(1024, 2, 1)
                
                
        #boundary enhancement part        
#         self.fuse = nn.Sequential(nn.Conv2d(5, 64, 1),nn.ReLU(inplace=True))
        self.fuse = nn.Sequential(nn.Conv2d(5, 5, 1),nn.ReLU(inplace=True))
#         self.fuse = double_conv(5,5)
#         self.fuse = nn.Conv2d(5, 64, 1)
        
#         self.SE_mimic = nn.Sequential(        
#             nn.Linear(64, 64, bias=False),
#             nn.ReLU(inplace=True),
#             nn.Linear(64, 5, bias=False),
#             nn.Sigmoid()
#         )
        self.SE_mimic = nn.Sequential(        
            nn.Linear(5, 5, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(5, 5, bias=False),
            nn.Sigmoid()
        )
        self.final_boundary = nn.Conv2d(5,2,1)
        
        self.final_conv = nn.Sequential(
            nn.Conv2d(128,64,3, padding=1),
            nn.ReLU(inplace=True)            
        )
 
        self.final_mask = nn.Conv2d(64,2,1)
        
                

        self.relu = nn.ReLU()        
        self.out = nn.Conv2d(64,1,1)

    def forward(self, x):
        h = x.size(2)
        w = x.size(3)

    
        conv1 = self.dconv_down1(x)
        x = self.maxpool(conv1)
        conv2 = self.dconv_down2(x)
        x = self.maxpool(conv2)        
        conv3 = self.dconv_down3(x)
        x = self.maxpool(conv3)        
        conv4 = self.dconv_down4(x)
        x = self.maxpool(conv4)        
        conv5 = self.dconv_down5(x)        
        x = self.upsample5(conv5)        
        x = torch.cat([x, conv4],1)        
        x = self.dconv_up4(x)
        x = self.upsample4(x) 
        x = torch.cat([x, conv3], dim=1)        
        x = self.dconv_up3(x)
        x = self.upsample3(x)        
        x = torch.cat([x, conv2], dim=1)  
        x = self.dconv_up2(x)
        x = self.upsample2(x)        
        x = torch.cat([x, conv1], dim=1)           
        x = self.dconv_up1(x)
        
        
        
        ## side output
        d1 = self.dsn1(conv1)
        d2 = F.upsample_bilinear(self.dsn2(conv2), size=(h,w))
        d3 = F.upsample_bilinear(self.dsn3(conv3), size=(h,w))
        d4 = F.upsample_bilinear(self.dsn4(conv4), size=(h,w))
        d5 = F.upsample_bilinear(self.dsn5(conv5), size=(h,w))
        
#         ###############softmax ver
        d1_out = F.softmax(d1,dim=1)
        d1_out = torch.unsqueeze(d1_out[:,1,:,:],1) 
        d2_out = F.softmax(d2,dim=1)
        d2_out = torch.unsqueeze(d2_out[:,1,:,:],1) 
        d3_out = F.softmax(d3,dim=1)
        d3_out = torch.unsqueeze(d3_out[:,1,:,:],1) 
        d4_out = F.softmax(d4,dim=1)
        d4_out = torch.unsqueeze(d4_out[:,1,:,:],1) 
        d5_out = F.softmax(d5,dim=1)
        d5_out = torch.unsqueeze(d5_out[:,1,:,:],1) 
        
        ###########sigmoid ver
#         d1_out = F.sigmoid(d1)
#         d2_out = F.sigmoid(d2)
#         d3_out = F.sigmoid(d3)
#         d4_out = F.sigmoid(d4)
#         d5_out = F.sigmoid(d5)

#         d1 = F.relu(d1)
#         d2 = F.relu(d2)
#         d3 = F.relu(d3)
#         d4 = F.relu(d4)
#         d5 = F.relu(d5)

#         concat = torch.cat((d1, d2, d3, d4, d5), 1)
        concat = torch.cat((d1_out, d2_out, d3_out, d4_out, d5_out), 1)
#         d1 = F.sigmoid(d1)
#         d2 = F.sigmoid(d2)
#         d3 = F.sigmoid(d3)
#         d4 = F.sigmoid(d4)
#         d5 = F.sigmoid(d5)
        ######################
        
        fuse_box = self.fuse(concat)
        GAP = F.adaptive_avg_pool2d(fuse_box,(1,1))
        GAP = GAP.view(-1, 5)
        
        se_like = self.SE_mimic(GAP)
        
        se_like = torch.unsqueeze(se_like, 2)
        se_like = torch.unsqueeze(se_like, 3)

# ##### 1 channel ver        
#         feat_se = concat * se_like.expand_as(concat)
        feat_se = fuse_box * se_like.expand_as(concat)
        boundary = self.final_boundary(feat_se)
        boundary_out = torch.unsqueeze(boundary[:,1,:,:],1)
#         boundary_out = F.sigmoid(boundary_out)
        
        bd_sftmax = F.softmax(boundary, dim=1)
        boundary_scale = torch.unsqueeze(bd_sftmax[:,1,:,:],1)        
        
#         feat_concat = torch.cat( [x, fuse_box], 1)
#         feat_concat_conv = self.final_conv(feat_concat)
#         mask = self.final_mask(feat_concat_conv)
        mask = self.final_mask(x)
        mask_sftmax = F.softmax(mask,dim=1)        
        mask_scale = torch.unsqueeze(mask_sftmax[:,1,:,:],1)
#         boudary_sig = F.softmax(boundary)
#         mask_sig = F.softmax(mask)
#         boundary_sig = F.sigmoid(boundary)
#         mask_sig = F.sigmoid(mask)

        scalefactor = torch.clamp(mask_scale+boundary_scale,0,1)
                        
    #ver2
#         mask_out = mask[:,1,:,:]
#         relu = self.relu(mask_out)
#         mask_out = (mask_out-relu)+ torch.mul(relu,scalefactor)
#         mask_out = F.sigmoid(mask_out)

    #ver3
        mask_out = torch.unsqueeze(mask[:,1,:,:],1)
        relu = self.relu(mask_out)        
        scalar = relu.cpu().detach().numpy()
#         print(np.sum(scalar))
        if np.sum(scalar) == 0:
            average = 0
        else : 
            average = scalar[np.nonzero(scalar)].mean()
        
        
        avg = F.adaptive_avg_pool2d(relu,(1,1))
        avg = avg.view(-1,1)        
        avg = torch.unsqueeze(avg,2)
        avg = torch.unsqueeze(avg,3)
        mask_out = (mask_out-relu)+ avg.expand_as(scalefactor) *scalefactor
        mask_out = mask_out-relu + (average*scalefactor)

#         mask_out = F.sigmoid(mask_out)
#         boundary_out = F.sigmoid(boundary_out)
# ##         return d1, d2, d3, d4, d5, boundary_out, mask_out
#         return d1_out, d2_out, d3_out, d4_out, d5_out, boundary_out, mask_out
        return d1, d2, d3, d4, d5, boundary_scale, mask_out, mask_scale, scalefactor
        
