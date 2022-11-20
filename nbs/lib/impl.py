# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_impl.ipynb.

# %% auto 0
__all__ = ['in_stats', 'tfms', 'train', 'val', 'image', 'label', 'f', 'pool_idxs', 'sigmas', 'save_hook', 'pos_sigmas']

# %% ../01_impl.ipynb 4
from typing import Tuple
import torch, torch.utils.data, torch.nn as nn, torch.nn.functional as F
import torchvision.transforms as T
from torchvision.datasets import ImageNet
from torchvision.models import vgg16, VGG16_Weights, vgg11, VGG11_Weights, alexnet, AlexNet_Weights
from lovely_tensors import monkey_patch
from torchinfo import summary

# %% ../01_impl.ipynb 5
monkey_patch()

# %% ../01_impl.ipynb 7
in_stats = ( (0.485, 0.456, 0.406),     # mean 
             (0.229, 0.224, 0.225) )    # std

tfms = T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=in_stats[0], std=in_stats[1])
    ])

train = ImageNet(root="~/work/datasets/ImageNet", split="train", transform=tfms)
val = ImageNet(root="~/work/datasets/ImageNet", split="val", transform=tfms)

# %% ../01_impl.ipynb 8
image, label = train[0]

print(f"Label: {label} Image: {image}")
image.rgb(denorm=in_stats)

# %% ../01_impl.ipynb 13
# The feature extractor part of the model
f: nn.Sequential = alexnet(weights=AlexNet_Weights.DEFAULT).features
f.requires_grad_(False).eval()

for l in f:
    # Disable inplace for ReLU and Dropout.
    # Otherwise they overwrite the previous layers output.
    if hasattr(l, "inplace"):
        l.inplace = False
f

# %% ../01_impl.ipynb 17
def sigmas(x: torch.Tensor, n=3):
    x /= x.std()*n*2 # *2 because I want +/- n sigmas
    return x - x.mean() + 0.5

# %% ../01_impl.ipynb 23
def save_hook(m: nn.Module, i: Tuple[torch.Tensor], o: torch.Tensor):
    m.inp = i[0] # torch passses a tuple because that's how forward() works in general.
    m.out = o

for l in f:
    if not hasattr(l, "hooked"):
        l.register_forward_hook(save_hook)
        l.hooked=True

f(image[None]) # Outputs 6x6x256 feature map, but we only care about the layer activations.

# %% ../01_impl.ipynb 25
for i, l in enumerate(f):
    print(f"{i}: {l}")
    if not i: print(f"\tIn:  {l.inp}") # For other layers, input=previous layers output.
    print(f"\tOut: {l.out}")

# %% ../01_impl.ipynb 27
pool_idxs = [ i for i in range(len(f)) if isinstance(f[i], nn.MaxPool2d) ]
pool_idxs

# %% ../01_impl.ipynb 36
def pos_sigmas(x: torch.Tensor, n=2):
    "Give n an input of non-negative numbers, rescale it fit nσ into [0..1] range"
    return x / (n * (x[ x> 0 ].std()))
