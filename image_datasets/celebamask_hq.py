import os
import random
import numpy as np
import pandas as pd
from PIL import Image
from typing import Optional, Callable

import torch
import torchvision.transforms as T
import torchvision.transforms.functional as TF
from torchvision.datasets import VisionDataset

from .utils import extract_images


class CelebAMaskHQ(VisionDataset):
    """The CelebAMask-HQ Dataset.

    Please organize the dataset in the following file structure:

    root
    ├── CelebA-HQ-img
    │   ├── 0.jpg
    │   ├── ...
    │   └── 29999.jpg
    ├── CelebA-HQ-to-CelebA-mapping.txt
    ├── CelebAMask-HQ-attribute-anno.txt
    ├── CelebAMask-HQ-mask-anno
    ├── CelebAMask-HQ-mask
    │   ├── 0.jpg
    │   ├── ...
    │   └── 29999.jpg
    ├── CelebAMask-HQ-mask-color
    │   ├── 0.jpg
    │   ├── ...
    │   └── 29999.jpg
    ├── CelebAMask-HQ-pose-anno.txt
    └── README.txt

    The train/valid/test sets are split according to the original CelebA dataset, resulting in
    24,183 training images, 2,993 validation images, and 2,824 test images.

    References:
      - https://paperswithcode.com/dataset/celebamask-hq
      - https://github.com/switchablenorms/CelebAMask-HQ

    """

    def __init__(
            self,
            root: str,
            split: str = 'train',
            transforms: Optional[Callable] = None,
    ):
        super().__init__(root=root, transforms=transforms)
        if split not in ['train', 'valid', 'test', 'all']:
            raise ValueError(f'Invalid split: {split}')
        self.split = split

        # Check file structure
        image_root = os.path.join(self.root, 'CelebA-HQ-img')
        mask_root = os.path.join(self.root, 'CelebAMask-HQ-mask')
        mask_color_root = os.path.join(self.root, 'CelebAMask-HQ-mask-color')
        mapping_file = os.path.join(self.root, 'CelebA-HQ-to-CelebA-mapping.txt')
        if not os.path.isdir(image_root):
            raise ValueError(f'{image_root} is not an existing directory')
        if not os.path.isdir(mask_root):
            raise ValueError(f'{mask_root} is not an existing directory')
        if not os.path.isdir(mask_color_root):
            raise ValueError(f'{mask_color_root} is not an existing directory')
        if not os.path.isfile(mapping_file):
            raise ValueError(f'{mapping_file} is not an existing file')

        # Read the mapping file
        mapping = pd.read_table(mapping_file, sep=r'\s+', index_col=0)
        mapping = {i: int(mapping.iloc[i]['orig_idx']) for i in range(30000)}

        def filter_func(p):
            if split == 'all':
                return True
            orig_idx = mapping[int(os.path.splitext(os.path.basename(p))[0])]
            celeba_splits = [0, 162770, 182637, 202599]
            k = 0 if split == 'train' else (1 if split == 'valid' else 2)
            return celeba_splits[k] <= orig_idx < celeba_splits[k+1]

        # Extract image paths
        self.img_paths = extract_images(image_root)
        self.mask_paths = extract_images(mask_root)
        self.mask_color_paths = extract_images(mask_color_root)
        self.img_paths = list(filter(filter_func, self.img_paths))
        self.mask_paths = list(filter(filter_func, self.mask_paths))
        self.mask_color_paths = list(filter(filter_func, self.mask_color_paths))

    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, item):
        X = Image.open(self.img_paths[item]).convert('RGB')
        mask = Image.open(self.mask_paths[item]).convert('L')
        mask_color = Image.open(self.mask_color_paths[item]).convert('RGB')
        if self.transforms is not None:
            X, mask, mask_color = self.transforms(X, mask, mask_color)
        return X, mask, mask_color


# ===============================================================================================
# Below are custom transforms that apply to image, mask and mask_color simultaneously
# Adapted from https://github.com/pytorch/vision/blob/main/references/segmentation/transforms.py
# ===============================================================================================

class Compose:
    def __init__(self, transforms):
        self.transforms = transforms

    def __call__(self, image, mask, mask_color):
        for t in self.transforms:
            image, mask, mask_color = t(image, mask, mask_color)
        return image, mask, mask_color


class Resize:
    def __init__(self, size):
        self.size = size

    def __call__(self, image, mask, mask_color):
        image = TF.resize(image, self.size, antialias=True)
        mask = TF.resize(mask, self.size, interpolation=T.InterpolationMode.NEAREST)
        mask_color = TF.resize(mask_color, self.size, interpolation=T.InterpolationMode.NEAREST)
        return image, mask, mask_color


class RandomHorizontalFlip:
    def __init__(self, flip_prob):
        self.flip_prob = flip_prob

    def __call__(self, image, mask, mask_color):
        if random.random() < self.flip_prob:
            image = TF.hflip(image)
            mask = TF.hflip(mask)
            mask_color = TF.hflip(mask_color)
        return image, mask, mask_color


class ToTensor:
    def __call__(self, image, mask, mask_color):
        image = TF.to_tensor(image)
        mask = torch.as_tensor(np.array(mask), dtype=torch.int64)
        mask_color = TF.to_tensor(mask_color)
        return image, mask, mask_color


class Normalize:
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, image, mask, mask_color):
        image = TF.normalize(image, mean=self.mean, std=self.std)
        mask_color = TF.normalize(mask_color, mean=self.mean, std=self.std)
        return image, mask, mask_color
