import torch
from anomalib.models import SuperSimpleNet

class IncrementalSuperSimpleNet(SuperSimpleNet):
    """SuperSimpleNet with alignment loss for incremental learning."""

    def __init__(self, old_weights=None, beta: float = 0.1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.beta = beta
        self.old_weights = {}
        if old_weights is not None:
            for name, param in old_weights.items():
                # store a detached copy to avoid updates
                self.old_weights[name] = param.clone().detach()

    def _alignment_loss(self) -> torch.Tensor:
        alignment_loss = torch.tensor(0.0, device=next(self.parameters()).device)
        count = 0
        for name, param in self.named_parameters():
            if name in self.old_weights and 'weight' in name and param.requires_grad:
                weight_diff = param - self.old_weights[name]
                alignment_loss = alignment_loss + torch.norm(weight_diff, p=2) ** 2
                count += 1
        if count > 0:
            alignment_loss = alignment_loss / count * self.beta
        return alignment_loss

    def training_step(self, batch, batch_idx):
        outputs = super().training_step(batch, batch_idx)
        loss = outputs['loss'] if isinstance(outputs, dict) else outputs
        loss = loss + self._alignment_loss()
        if isinstance(outputs, dict):
            outputs['loss'] = loss
            return outputs
        return loss
