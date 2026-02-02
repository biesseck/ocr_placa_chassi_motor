import torch.nn as nn
import torch.nn.functional as F


class ResBlock(nn.Module):
    def __init__(self, in_channels, out_channels, filter_size=3, inner_layers=1):
        super(ResBlock, self).__init__()
        layers = []
        for _ in range(inner_layers):
            layers.append(nn.Conv2d(in_channels, out_channels, filter_size, padding=filter_size // 2))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU(inplace=True))
        layers.append(nn.Conv2d(in_channels, out_channels, filter_size, padding=filter_size // 2))
        layers.append(nn.BatchNorm2d(out_channels))
        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        return F.relu(x + self.layers(x), inplace=True)


class ConvBatch(nn.Module):
    def __init__(self, in_channels, out_channels, filter_size, activation='relu', padding='same', stride=(1, 1)):
        super(ConvBatch, self).__init__()
        self.conv = nn.Conv2d(in_channels, out_channels, filter_size, padding=filter_size // 2, stride=stride)
        self.bn = nn.BatchNorm2d(out_channels)
        self.activation = activation

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        if self.activation == 'relu':
            return F.relu(x, inplace=True)
        else:
            return x
