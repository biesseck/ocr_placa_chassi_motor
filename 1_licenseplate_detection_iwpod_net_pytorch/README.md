# IWPOD-NET in Pytorch

This repository is Pytorch implementation of [A Flexible Approach for Automatic License Plate Recognition in Unconstrained Scenarios](https://doi.org/10.1109/TITS.2021.3055946). The referenced tensorflow and keras codes can be found [here](https://github.com/claudiojung/iwpod-net).

![20230602_171136](https://github.com/blastak/iwpod-net-pytorch/assets/12149098/fb96f4b9-49a8-4b70-a99c-88db969708a2 "Results are shown in green, ground-truth annotations in red.")

## Package Dependency
- python 3.8.16
- pytorch 2.0.1 with CUDA 11.8
- opencv-python 4.7.0

## Setup environments with conda
```conda create --name iwpod-net-pytorch python=3.8.16```

```conda activate iwpod-net-pytorch```

```pip install torch --index-url https://download.pytorch.org/whl/cu118```

```pip install opencv-python==4.7.0.72```

## Training

use ```train.py```

## Inferencing

use ```detect.py```

## NOTE

The file that exists in path ```weights/``` is learned only up to 10,000 epochs. You can continue learning using this, or you can learn from scratch without using this file.

