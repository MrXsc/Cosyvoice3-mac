<div align="center">

# 🎙️ Cosyvoice3-mac

**在 Apple Silicon Mac 上本地运行 CosyVoice3 语音克隆**

一段 5~10 秒参考音频，克隆任意音色。纯本地推理 · 免费 · 离线

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![macOS](https://img.shields.io/badge/macOS-Apple_Silicon-black?logo=apple&logoColor=white)](https://support.apple.com/mac)
[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)](https://www.python.org)
[![Model](https://img.shields.io/badge/Model-Fun--CosyVoice3--0.5B-orange)](https://www.modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512)
[![Status](https://img.shields.io/badge/Status-v0.1_CPU_版-green)](#-快速开始)

*基于官方 [CosyVoice3](https://github.com/FunAudioLLM/CosyVoice) 做 macOS 适配：MPS 补丁 · 最小化依赖 · 一键安装*
*环境踩坑方案参考 [cosyvoice2-mac](https://github.com/BreetyGreen/cosyvoice2-mac)（MIT）*

</div>

---

## ✨ 特性

| | |
|---|---|
| 🎯 **零样本克隆** | 5~10 秒参考音频 + 一句话参考文字，无需训练 |
| 🌐 **两种模式** | `zero-shot`（音色贴） / `cross-lingual`（免参考文字，更稳） |
| 🏆 **RL 权重** | `--rl` 一键切换强化学习权重，韵律更自然（实测推荐） |
| 🧹 **音频自动清洗** | 降噪 + 响度归一化 + 切静音，脏录音也能用（可关） |
| 💎 **输出润色** | 自动响度归一化 + 44.1kHz 重采样 |
| 📦 **最小依赖** | ~30 包（官方 ~40+），全部国内镜像可装，逐行注释说明用途 |
| ⚡ **MPS 补丁** | Metal GPU 补丁就绪（实验性：实测与 CPU 打平，见性能一节） |

## 📦 安装

```bash
git clone https://github.com/MrXsc/Cosyvoice3-mac.git
cd Cosyvoice3-mac
bash install.sh
```

> 脚本幂等：网络中断后重跑即断点续传。自动完成 conda 环境（py3.10 + pynini + ffmpeg）、依赖安装、CosyVoice 源码（含 Matcha-TTS 子模块）、MPS 补丁套用、模型下载与校验。

<details>
<summary><b>手动部署</b>（与 install.sh 等价）</summary>

```bash
conda create -n cosyvoice -c conda-forge --override-channels \
    python=3.10 pynini=2.1.5 ffmpeg "setuptools<81" numpy=1.26.4 pip -y
conda activate cosyvoice
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install -r requirements.mac.txt

git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git
cd CosyVoice && git apply ../patches/0001-macos-mps-device.patch && cd ..
python scripts/download_model.py
```
</details>

<details>
<summary><b>模型下载</b>（模型可放任意路径，用 <code>--model-dir</code> 指定）</summary>

```bash
# 方式一：ModelScope 命令行（推荐，断点续传）
pip install modelscope
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 \
    --local_dir CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B

# 方式二：本仓库脚本（逐文件下载 + 远端大小校验，更抗中断）
python scripts/download_model.py
```
</details>

## 🚀 快速开始

```bash
conda activate cosyvoice

# zero-shot 克隆（推荐）：参考音频 + 它的原话 + 目标文字
TEXT_ECHO_DEVICE=cpu python scripts/tts_cv3.py \
    --ref your_ref.m4a \
    --prompt-text "参考音频里说的原话" \
    --text "要合成的目标文字" \
    --out result.wav

# cross-lingual：免参考文字，不吃听写错误
TEXT_ECHO_DEVICE=cpu python scripts/tts_cv3.py \
    --ref your_ref.m4a \
    --text "要合成的目标文字" \
    --no-prompt-text \
    --out result.wav
```

<details>
<summary><b>全部参数</b></summary>

| 参数 | 说明 |
|---|---|
| `TEXT_ECHO_DEVICE=cpu\|mps` | 推理设备（MPS 需 `PYTORCH_ENABLE_MPS_FALLBACK=1`） |
| `--model-dir` | 模型路径（默认 `CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B`） |
| `--rl` | 用 RL 强化学习权重（韵律更自然，实测推荐） |
| `--clip-seconds N` | 参考音频取前 N 秒（5~10 最佳；0=不截取） |
| `--no-denoise` | 清洗时不降噪（人声干净时用，避免发闷） |
| `--no-clean` | 完全关闭参考音频清洗 |
| `--out` | 输出 wav 路径 |

</details>

## 💡 效果经验

1. **克隆相似度 ~70% 由参考音频质量决定**：单人、无背景音乐、吐字清楚、纯一种语言、5~10 秒、情绪平稳
2. **RL 权重（`--rl`）优于 base**：韵律更自然
3. **参考文字必须与录音一字不差**；听不准就用 cross-lingual 模式绕开
4. 合成文本长度最好 ≥ 参考文字的一半，过短会触发模型警告
5. 模型原生输出 24kHz，脚本自动输出润色版

## 🗂️ 项目结构

```
Cosyvoice3-mac/
├── install.sh              # 幂等一键部署
├── environment.yml         # conda 环境定义
├── requirements.mac.txt    # 最小依赖清单（逐行注释用途）
├── patches/                # 对上游 CosyVoice 的 MPS 补丁
├── scripts/
│   ├── tts_cv3.py          # 日常合成 CLI
│   ├── smoke_cv3.py        # 快速实验 / A-B 对比
│   └── download_model.py   # ModelScope 逐文件下载 + 校验
└── CosyVoice/              # install.sh 自动拉取的上游源码 + 模型（不入库）
```

<details>
<summary><b>MPS 补丁说明</b></summary>

官方代码设备逻辑写死 `cuda else cpu`，Mac 上会静默跑 CPU。`patches/0001-macos-mps-device.patch` 修改：

- `cosyvoice/cli/model.py`：`get_device()`（cuda→MPS→cpu，支持 `TEXT_ECHO_DEVICE` 覆盖）、设备无关 autocast、`torch.mps.empty_cache()`
- `cosyvoice/hifigan/generator.py`：MPS 不支持 float64，f0 预测回 CPU

上游代码不入库，CosyVoice 升级后重新 `git apply` 即可。
</details>

## ⚡ 性能实测（Apple M4 / 24GB）

合成 9.5 秒音频（zero-shot + RL，fp32）：

| 配置 | 耗时 | RTF |
|---|---|---|
| **torch 2.3.1 + CPU**（默认，推荐） | **37s** | ~4.0 |
| torch 2.3.1 + MPS | 40s | 4.3 |
| torch 2.6.0 + MPS | 50s | 5.3 |
| torch 2.6.0 + CPU | 49s | 5.3 |

结论：**CPU 是当前最优配置**。0.5B 模型的自回归解码瓶颈在调度而非算力，MPS 暂无收益（已实测 torch 2.3.1 / 2.6.0 两代后端）；MPS 补丁保留给未来更大模型或长文本场景。首次合成含模型加载（约 10s），之后每条即上表耗时。

## ⚠️ 合规提醒

语音克隆仅用于：**你自己的声音** / **已获明确授权的声音**。不要克隆影视角色、特定艺人或他人的声线用于欺骗或商用（声音权、肖像权、IP 授权风险）。

## 🙏 致谢

- [CosyVoice / Fun-CosyVoice3](https://github.com/FunAudioLLM/CosyVoice) — FunAudioLLM / 阿里通义实验室（Apache-2.0）
- [cosyvoice2-mac](https://github.com/BreetyGreen/cosyvoice2-mac)（MIT）— 环境踩坑方案的起点
- 模型权重：[ModelScope: FunAudioLLM/Fun-CosyVoice3-0.5B-2512](https://www.modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512)

<div align="center">

**MIT License** · 如果这个项目对你有帮助，欢迎 ⭐ Star 支持

</div>
