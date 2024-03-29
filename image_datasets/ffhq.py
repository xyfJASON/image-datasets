import os
from PIL import Image
from typing import Optional, Callable

import torchvision.transforms as T
from torch.utils.data import Dataset

from .utils import extract_images


class FFHQ(Dataset):
    """The Flickr-Faces-HQ (FFHQ) Dataset.

    Flickr-Faces-HQ (FFHQ) consists of 70,000 high-quality PNG images at 1024×1024 resolution and contains
    considerable variation in terms of age, ethnicity and image background. It also has good coverage of
    accessories such as eyeglasses, sunglasses, hats, etc. The images were crawled from Flickr, thus inheriting
    all the biases of that website, and automatically aligned and cropped using dlib. Only images under
    permissive licenses were collected. Various automatic filters were used to prune the set, and finally
    Amazon Mechanical Turk was used to remove the occasional statues, paintings, or photos of photos.
    (Copied from PapersWithCode)

    There are several versions of the dataset in the official Google Drive link, among which `images1024x1024`
    is the most widely used one. To load data with this class, the dataset should be organized in the following
    structure:

    root
    ├── ffhq-dataset-v2.json
    ├── LICENSE.txt
    ├── README.txt
    ├── thumbnails128x128
    │   ├── 00000.png
    │   ├── ...
    │   └── 69999.png
    └── images1024x1024
        ├── 00000.png
        ├── ...
        └── 69999.png

    This class has one pre-defined transform:
      - 'resize' (default): Resize the image directly to the target size

    Reference:
      - https://github.com/NVlabs/ffhq-dataset
      - https://paperswithcode.com/dataset/ffhq
      - https://drive.google.com/drive/folders/1tZUcXDBeOibC6jcMCtgRRz67pzrAHeHL

    """

    def __init__(
            self,
            root: str,
            img_size: int,
            split: str = 'train',
            version: str = 'images1024x1024',
            transform_type: Optional[str] = 'resize',
            transform: Optional[Callable] = None,
    ):
        if split not in ['train', 'test', 'all']:
            raise ValueError(f'Invalid split: {split}')
        if version not in ['images1024x1024', 'thumbnails128x128']:
            raise ValueError(f'Invalid version: {version}')
        if transform_type not in ['resize', 'none'] and transform_type is not None:
            raise ValueError(f'Invalid transform_type: {transform_type}')

        root = os.path.expanduser(root)
        image_root = os.path.join(root, version)
        if not os.path.isdir(image_root):
            raise ValueError(f'{image_root} is not an existing directory')

        self.img_size = img_size
        self.split = split
        self.version = version
        self.transform_type = transform_type
        self.transform = transform
        if transform is None:
            self.transform = self.get_transform()

        self.img_paths = extract_images(image_root)
        if split == 'train':
            self.img_paths = list(filter(lambda p: 0 <= int(os.path.basename(p).split('.')[0]) < 60000, self.img_paths))
        elif split == 'test':
            self.img_paths = list(filter(lambda p: 60000 <= int(os.path.basename(p).split('.')[0]) < 70000, self.img_paths))

    def __len__(self):
        return len(self.img_paths)

    def __getitem__(self, item):
        X = Image.open(self.img_paths[item])
        if self.transform is not None:
            X = self.transform(X)
        return X

    def get_transform(self):
        flip_p = 0.5 if self.split in ['train', 'all'] else 0.0
        if self.transform_type == 'resize':
            transform = T.Compose([
                T.Resize((self.img_size, self.img_size), antialias=True),
                T.RandomHorizontalFlip(flip_p),
                T.ToTensor(),
                T.Normalize([0.5] * 3, [0.5] * 3),
            ])
        elif self.transform_type == 'none' or self.transform_type is None:
            transform = None
        else:
            raise ValueError(f'Invalid transform_type: {self.transform_type}')
        return transform
