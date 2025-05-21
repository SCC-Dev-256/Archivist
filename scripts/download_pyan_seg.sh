import os
import torch
import torch.torch_version
from pyannote.audio import Model
from omegaconf import ListConfig
from omegaconf.base import ContainerMetadata, Metadata
from omegaconf.nodes import AnyNode
from typing import Any
import collections

# Add required classes to safe globals for PyTorch 2.6+
torch.serialization.add_safe_globals([
    ListConfig, ContainerMetadata, Metadata, Any, list, collections.defaultdict, dict, int, AnyNode,
    torch.torch_version.TorchVersion
])

# Set the target directory
target_dir = "/opt/Archivist/.venv/lib/python3.11/site-packages/whisperx/assets"
os.makedirs(target_dir, exist_ok=True)

def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return torch.load(*args, **kwargs)

# Patch torch.load globally (for this script)
import lightning_fabric.utilities.cloud_io
lightning_fabric.utilities.cloud_io.pl_load = patched_load

# Download the model to the specific location
model = Model.from_pretrained(
    "pyannote/segmentation",
    use_auth_token="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",
    cache_dir=target_dir
)

# Verify the downloaded model file size
model_file = os.path.join(target_dir, 'pytorch_model.bin')
if os.path.exists(model_file):
    file_size = os.path.getsize(model_file)
    if file_size == 0:
        raise ValueError('Downloaded model file is empty. Please check the download process.')
    elif file_size < 1000:  # Arbitrary size check, adjust as needed
        raise ValueError('Downloaded model file is too small. Please check the download process.')
    else:
        print(f'Model file downloaded successfully with size: {file_size} bytes.')
else:
    raise FileNotFoundError('Model file was not downloaded. Please check the download process.')
