import os
import torch
from torch.utils.data import Dataset
from src.utils import *
from src.label import *
from src.sampler import augment_sample, labels2output_map
import cv2

def image_label_loader(data_path):
    Files = image_files_from_folder(data_path)
    fakepts = np.array([[0.5, 0.5001, 0.5001, 0.5], [0.5, 0.5, 0.5001, 0.5001]])
    fakeshape = Shape(fakepts)
    Data = []
    ann_files = 0
    for file in Files:
        labfile = os.path.splitext(file)[0] + '.txt'
        if os.path.isfile(labfile):
            ann_files += 1
            L = readShapes(labfile)
            I = cv2.imread(file)
            if len(L) > 0:
                Data.append([I, L])
        else:
            # Appends a "fake" plate to images without any annotation
            I = cv2.imread(file)
            Data.append([I, [fakeshape]])

    print('%d images with labels found' % len(Data))
    print('%d annotation files found' % ann_files)

    return Data

class ALPRDataset(Dataset):
    def __init__(self, data_path, dim=208, stride=16):
        self.dim = dim
        self.stride = stride
        self.data = image_label_loader(data_path)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        X, llp, ptslist = augment_sample(self.data[index][0], self.data[index][1], self.dim)
        y = labels2output_map(llp, ptslist, self.dim, self.stride, alpha=0.5)

        XX = torch.from_numpy(X).permute(2, 0, 1).float()
        YY = torch.from_numpy(y).permute(2, 0, 1).float()
        return XX, YY

