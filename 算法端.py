import os
from typing import Optional, List, Tuple

from anomalib.data import Folder
from anomalib.models import Patchcore
from anomalib.engine.engine import Engine



class AlgoSystem:
    def __init__(
            self,
            name: str,
            root: str,
            normal_dir: str = "train/OK",
            abnormal_dir: str = "test/NG",
            normal_test_dir: str = "test/OK",
            extensions: Tuple[str, ...] = (".jpg",),
            val_split_ratio: float = 0.5,
            normalization_method: str = "min_max",
            image_metrics: Optional[List[str]] = None,
    ):
        self.datamodule = Folder(
            name=name,
            root=root,
            normal_dir=normal_dir,
            abnormal_dir=abnormal_dir,
            normal_test_dir=normal_test_dir,
            mask_dir=None,
            extensions=extensions,
            val_split_ratio=val_split_ratio
        )
        self.datamodule.setup()
        self.engine = Engine(
            default_root_dir="results"  # 日志和权重输出目录
        )

    def train(
            self,
            layers: list[str],
            backbone: str = "wide_resnet50_2",
            coreset_sampling_ratio: float = 0.1,
            num_neighbors: int = 9,
    ):
        model = Patchcore(
            backbone=backbone,
            layers=layers,
            coreset_sampling_ratio=coreset_sampling_ratio,
            num_neighbors=num_neighbors,
        )
        self.engine.fit(model=model, datamodule=self.datamodule)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_root = os.path.join(base_dir, "data", "2150155000_PC1")

    system = AlgoSystem(
        name="2150155000_PC1",
        root=data_root,
        normalization_method="min_max",
        image_metrics=["F1Score", "AUROC"],
    )
    system.train(
        backbone="resnet18",
        layers=['layer1','layer2','layer3'],
        coreset_sampling_ratio=0.1,
        num_neighbors=9,
    )
