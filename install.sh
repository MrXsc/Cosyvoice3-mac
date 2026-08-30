#!/usr/bin/env bash
#
# install.sh — TextEcho: macOS (Apple Silicon) 部署 Fun-CosyVoice3-0.5B
#
# 幂等：已完成的步骤自动跳过，可反复运行；网络中断后重跑即断点续传。
# 与 cosyvoice2-mac 的差异：不依赖 brew（conda-forge 直接提供 ffmpeg），
# 全程 TUNA/阿里镜像，模型为 Fun-CosyVoice3-0.5B-2512。
#
# 用法：  bash install.sh
set -e

ENV_NAME="cosyvoice"
WORKDIR="$(cd "$(dirname "$0")" && pwd)"
CONDA_BIN="${CONDA_BIN:-$HOME/miniconda3/bin/conda}"
COSYVOICE_DIR="$WORKDIR/CosyVoice"

echo "=========================================="
echo " TextEcho: Fun-CosyVoice3 macOS 部署"
echo " 工作目录: $WORKDIR"
echo "=========================================="

# 1. conda（不强制 brew；没有 conda 时用 Miniforge 官方脚本装到 ~/miniforge3）
if [[ ! -x "$CONDA_BIN" ]] && ! command -v conda >/dev/null 2>&1; then
  echo ">>> 未找到 conda，安装 Miniforge 到 ~/miniforge3 ..."
  curl -L -o /tmp/miniforge.sh \
    https://mirrors.tuna.tsinghua.edu.cn/github-release/conda-forge/miniforge/LatestRelease/Miniforge3-MacOSX-arm64.sh
  bash /tmp/miniforge.sh -b -p "$HOME/miniforge3"
  CONDA_BIN="$HOME/miniforge3/bin/conda"
fi
[[ -x "$CONDA_BIN" ]] || CONDA_BIN="$(command -v conda)"
echo "✅ conda: $CONDA_BIN"

# 2. conda 环境（py3.10 + pynini + ffmpeg + numpy/setuptools 锚点）
if ! "$CONDA_BIN" env list | grep -q "^$ENV_NAME "; then
  echo ">>> 创建 conda 环境 $ENV_NAME ..."
  "$CONDA_BIN" create -n "$ENV_NAME" -c conda-forge --override-channels \
    python=3.10 pynini=2.1.5 ffmpeg "setuptools<81" numpy=1.26.4 pip -y
fi
ENV_PY="$("$CONDA_BIN" info --base)/envs/$ENV_NAME/bin/python"
echo "✅ 环境: $("$ENV_PY" --version)"

# 3. pip 阿里镜像 + L0 依赖
"$ENV_PY" -m pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ >/dev/null
echo ">>> 安装 L0 依赖（requirements.mac.txt）..."
"$ENV_PY" -m pip install -r "$WORKDIR/requirements.mac.txt"

# 4. 上游源码（已有则跳过）
if [[ ! -f "$COSYVOICE_DIR/cosyvoice/cli/cosyvoice.py" ]]; then
  echo ">>> 克隆 CosyVoice 官方仓库（含 Matcha-TTS 子模块）..."
  git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git "$COSYVOICE_DIR"
fi

# 5. 套用 MPS 补丁
echo ">>> 套用 MPS 补丁..."
(cd "$COSYVOICE_DIR" && git apply --check "$WORKDIR/patches/0001-macos-mps-device.patch" 2>/dev/null \
  && git apply "$WORKDIR/patches/0001-macos-mps-device.patch" \
  || echo "✅ 补丁已应用或已包含（跳过）")

# 6. 模型下载（断点续传 + 文件校验）
"$ENV_PY" "$WORKDIR/scripts/download_model.py"

# 7. 快速验证
echo ">>> 验证 MPS ..."
"$ENV_PY" -c "import torch; assert torch.backends.mps.is_available(); print('MPS OK')"

echo "=========================================="
echo "🎉 部署完成！用法："
echo "  $ENV_PY $WORKDIR/scripts/tts_cv3.py --ref 你的参考音频.wav --text \"你好\" --no-prompt-text --out out.wav"
echo "=========================================="
