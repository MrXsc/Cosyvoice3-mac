#!/usr/bin/env python
"""下载 Fun-CosyVoice3-0.5B-2512 模型权重（ModelScope 逐文件 API，断点续传）。

不使用 snapshot_download 的 local_dir 同步模式——实测中断后恢复时会清空/破坏
目录（发生两次）。改为对 REQUIRED 逐文件 model_file_download：
文件已存在且大小与远端一致则跳过，否则续传补齐（自带 sha256 校验）。
"""
import os
import sys

from modelscope.hub.api import HubApi
from modelscope.hub.file_download import model_file_download

MODEL_ID = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
DEST = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "CosyVoice", "pretrained_models", "Fun-CosyVoice3-0.5B"
)

REQUIRED = [
    "llm.pt", "flow.pt", "hift.pt", "campplus.onnx", "speech_tokenizer_v3.onnx",
    "cosyvoice3.yaml",
    "CosyVoice-BlankEN/model.safetensors", "CosyVoice-BlankEN/vocab.json",
    "CosyVoice-BlankEN/tokenizer_config.json", "CosyVoice-BlankEN/config.json",
    "CosyVoice-BlankEN/generation_config.json", "CosyVoice-BlankEN/merges.txt",
]  # 注：仓库无 spk2info.pt，frontend.py 对其缺失是容忍的（os.path.exists 判断）


def main():
    print(f"目标下载目录: {DEST}")
    api = HubApi()
    remote = {f["Path"]: f.get("Size", 0)
              for f in api.get_model_files(MODEL_ID, recursive=True)
              if f["Type"] == "blob"}

    for f in REQUIRED:
        dst = os.path.join(DEST, f)
        if os.path.isfile(dst) and remote.get(f) in (0, os.path.getsize(dst)):
            print(f"OK    {f} ({os.path.getsize(dst)/1e6:.0f}MB)")
        else:
            print(f"DOWN  {f} ({remote.get(f, 0)/1e6:.0f}MB) ...")
            model_file_download(MODEL_ID, f, local_dir=DEST)

    bad = [f for f in REQUIRED
           if not os.path.isfile(os.path.join(DEST, f))
           or (remote.get(f, 0) and os.path.getsize(os.path.join(DEST, f)) != remote[f])]
    if bad:
        print("缺失/不完整，请重跑本脚本:", *bad, sep="\n  ")
        sys.exit(1)
    print("MODEL_DOWNLOAD_DONE，关键文件齐全")


if __name__ == "__main__":
    main()

# 手动下载（等价）：modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local_dir CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B