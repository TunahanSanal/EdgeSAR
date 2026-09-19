"""
EdgeSAR - MSTAR Dataset Loader & Preprocessing Pipeline
Sandia National Labs MSTAR SAR Target Benchmark (T-72, BMP-2, BTR-70).

Supports:
- Standard 17 deg (train) / 15 deg (test) depression angle protocol
- 5-Fold Stratified Cross-Validation
- Out-of-Distribution (OOD / Unknown Target) evaluation (2S1, BRDM2, BTR60, D7, T62, ZIL131, ZSU_23_4)
- Fast NPZ cached tensor loading with on-the-fly SAR data augmentation
"""

import os
import glob
from typing import Optional, List, Tuple, Dict, Union
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset, DataLoader, Subset
from sklearn.model_selection import StratifiedKFold


# Canonical class mapping strictly matching EdgeSAR ATR index
# 0: T-72, 1: BMP-2, 2: BTR-70
CLASS_MAPPING: Dict[str, int] = {
    "T72": 0,
    "T-72": 0,
    "BMP2": 1,
    "BMP-2": 1,
    "BTR70": 2,
    "BTR-70": 2,
}

CLASS_NAMES: List[str] = ["T-72", "BMP-2", "BTR-70"]

OOD_CLASS_NAMES: List[str] = [
    "2S1", "BRDM2", "BTR60", "D7", "T62", "ZIL131", "ZSU_23_4"
]


class MSTARDataset(Dataset):
    """
    PyTorch Dataset for MSTAR SAR target chips (128x128).
    Supports cached loading from .npz or raw JPEG directory scans.
    """

    def __init__(
        self,
        root_dir: str = "data/mstar",
        split: str = "train",  # 'train' (17 deg), 'test' (15 deg), 'all', 'ood'
        target_classes: Optional[List[str]] = None,
        transform=None,
        augment: bool = False,
    ):
        super().__init__()
        self.root_dir = root_dir
        self.split = split
        self.augment = augment
        self.transform = transform
        
        if target_classes is None:
            self.target_classes = ["T72", "BMP2", "BTR70"]
        else:
            self.target_classes = target_classes

        self.images: Optional[np.ndarray] = None
        self.labels: Optional[np.ndarray] = None
        self.samples: List[Tuple[str, int, str]] = []

        self._initialize_data()

    def _initialize_data(self):
        # Check for fast npz cache for standard splits
        if self.split in ["train", "test"]:
            cache_file = os.path.join(self.root_dir, f"{self.split}_cache.npz")
            if os.path.exists(cache_file):
                data = np.load(cache_file)
                self.images = data["images"]
                self.labels = data["labels"]
                return

        if self.split == "all":
            train_cache = os.path.join(self.root_dir, "train_cache.npz")
            test_cache = os.path.join(self.root_dir, "test_cache.npz")
            if os.path.exists(train_cache) and os.path.exists(test_cache):
                tr = np.load(train_cache)
                te = np.load(test_cache)
                self.images = np.concatenate([tr["images"], te["images"]], axis=0)
                self.labels = np.concatenate([tr["labels"], te["labels"]], axis=0)
                return

        # Fallback to file paths
        if self.split == "ood":
            ood_dir = os.path.join(self.root_dir, "ood")
            if not os.path.exists(ood_dir):
                raise FileNotFoundError(f"OOD directory not found: {ood_dir}")
            for ood_cls in sorted(os.listdir(ood_dir)):
                cls_path = os.path.join(ood_dir, ood_cls)
                if os.path.isdir(cls_path):
                    for img_file in glob.glob(os.path.join(cls_path, "*.jpeg")) + glob.glob(os.path.join(cls_path, "*.jpg")):
                        self.samples.append((img_file, -1, ood_cls))
            return

        splits_to_load = [self.split] if self.split in ["train", "test"] else ["train", "test"]
        for s in splits_to_load:
            s_dir = os.path.join(self.root_dir, s)
            if not os.path.exists(s_dir):
                raise FileNotFoundError(f"MSTAR split directory not found: {s_dir}")

            for cls_name in self.target_classes:
                cls_dir = os.path.join(s_dir, cls_name)
                if not os.path.isdir(cls_dir):
                    continue
                label = CLASS_MAPPING.get(cls_name, -1)
                img_files = glob.glob(os.path.join(cls_dir, "*.jpeg")) + glob.glob(os.path.join(cls_dir, "*.jpg"))
                for img_file in sorted(img_files):
                    self.samples.append((img_file, label, cls_name))

    def __len__(self) -> int:
        if self.images is not None:
            return len(self.images)
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        if self.images is not None:
            img_arr = self.images[idx].copy()
            label = int(self.labels[idx])
        else:
            img_path, label, _ = self.samples[idx]
            with Image.open(img_path) as img:
                img_arr = np.array(img.convert("L"), dtype=np.float32)
            if img_arr.shape != (128, 128):
                img_pil = Image.fromarray(img_arr.astype(np.uint8)).resize((128, 128), Image.BILINEAR)
                img_arr = np.array(img_pil, dtype=np.float32)
            max_val = np.max(img_arr)
            if max_val > 0:
                img_arr = img_arr / 255.0

        # Online augmentation for SAR images (train split only)
        if self.augment:
            if np.random.rand() > 0.5:
                img_arr = np.fliplr(img_arr).copy()
            if np.random.rand() > 0.5:
                img_arr = np.flipud(img_arr).copy()
            if np.random.rand() > 0.5:
                speckle = np.random.gamma(shape=10.0, scale=0.1, size=img_arr.shape).astype(np.float32)
                img_arr = np.clip(img_arr * speckle, 0.0, 1.0)

        tensor = torch.from_numpy(img_arr).unsqueeze(0)

        if self.transform is not None:
            tensor = self.transform(tensor)

        return tensor, label


def get_mstar_dataloaders(
    root_dir: str = "data/mstar",
    batch_size: int = 32,
    num_workers: int = 0,
    augment_train: bool = True,
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    train_dataset = MSTARDataset(root_dir=root_dir, split="train", augment=augment_train)
    test_dataset = MSTARDataset(root_dir=root_dir, split="test", augment=False)
    ood_dataset = MSTARDataset(root_dir=root_dir, split="ood", augment=False)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)
    ood_loader = DataLoader(ood_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers)

    return train_loader, test_loader, ood_loader


def get_mstar_kfold_loaders(
    root_dir: str = "data/mstar",
    n_splits: int = 5,
    batch_size: int = 32,
    seed: int = 42,
) -> List[Tuple[DataLoader, DataLoader]]:
    full_dataset = MSTARDataset(root_dir=root_dir, split="all", augment=False)
    
    if full_dataset.labels is not None:
        labels = full_dataset.labels
    else:
        labels = [label for _, label, _ in full_dataset.samples]
    indices = np.arange(len(full_dataset))

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold_loaders = []

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(indices, labels)):
        train_sub = Subset(MSTARDataset(root_dir=root_dir, split="all", augment=True), train_idx)
        val_sub = Subset(MSTARDataset(root_dir=root_dir, split="all", augment=False), val_idx)

        train_loader = DataLoader(train_sub, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_sub, batch_size=batch_size, shuffle=False)

        fold_loaders.append((train_loader, val_loader))

    return fold_loaders


if __name__ == "__main__":
    print("--- MSTAR Dataset Loader Fast Cache Test ---", flush=True)
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "mstar")
    train_loader, test_loader, ood_loader = get_mstar_dataloaders(root_dir=base_dir, batch_size=16)
    print(f"Train samples: {len(train_loader.dataset)} | Batches: {len(train_loader)}", flush=True)
    print(f"Test samples:  {len(test_loader.dataset)} | Batches: {len(test_loader)}", flush=True)
    print(f"OOD samples:   {len(ood_loader.dataset)} | Batches: {len(ood_loader)}", flush=True)
    
    x, y = next(iter(train_loader))
    print(f"Batch shape: {x.shape}, labels: {y.tolist()}", flush=True)
    
    folds = get_mstar_kfold_loaders(root_dir=base_dir, n_splits=5, batch_size=16)
    print(f"5-Fold CV initialized successfully with {len(folds)} folds.", flush=True)
    print("PASS: MSTAR Fast Cache Loader verified.", flush=True)
