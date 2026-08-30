# Cosyvoice3-mac — 在 macOS (Apple Silicon) 上本地运行 CosyVoice3 语音克隆

**v0.1（CPU 版）** · [English](#english) | 中文

在 **Apple Silicon Mac（M1/M2/M3/M4）** 上零基础部署 **Fun-CosyVoice3-0.5B**（阿里 FunAudioLLM 开源零样本 TTS），用一段 5~10 秒参考音频克隆音色，纯本地推理，免费、离线、数据不出机器。

> 适配经验源自 [cosyvoice2-mac](https://github.com/BreetyGreen/cosyvoice2-mac)（MIT），在其"环境绕坑"方案基础上，完成了 CosyVoice3 的 **MPS 补丁**与**最小化依赖**改造，并实测跑通 zero-shot / cross-lingual / RL 权重全链路。

## 特性

- ✅ 纯本地运行，免费、离线
- ✅ 零样本克隆：5~10 秒参考音频 + 一句话参考文字，无需训练
- ✅ 两种克隆模式：zero-shot（带参考文字，音色贴）/ cross-lingual（免参考文字，更稳）
- ✅ RL 强化学习权重一键切换（`--rl`），韵律更自然（实测推荐）
- ✅ 参考音频自动清洗：降噪 + 响度归一化 + 切静音（可关）
- ✅ 输出自动润色：响度归一化 + 44.1kHz 重采样
- ✅ MPS (Metal) GPU 补丁就绪（`patches/`，v0.1 实验性未完全验证；CPU 模式开箱即用）
- ✅ 最小化依赖（~30 包 vs 官方 ~40+），全部国内镜像可装

## 环境要求

| 项 | 要求 |
|---|---|
| 系统 | macOS（Apple Silicon 推荐） |
| 内存 | ≥ 16G（模型约 4.4G + 推理内存） |
| 磁盘 | 预留 ≥ 10G |
| 网络 | ModelScope / TUNA / 阿里镜像可达即可（不依赖 GitHub 直连） |

## 一键部署

```bash
git clone https://github.com/MrXsc/Cosyvoice3-mac.git
cd Cosyvoice3-mac
bash install.sh
```

脚本幂等：中断后重跑即断点续传。完成内容包括 conda 环境（py3.10 + pynini + ffmpeg）、L0 依赖、CosyVoice 源码（含 Matcha-TTS 子模块）、MPS 补丁套用、模型下载与校验。

<details>
<summary>手动部署（等价于 install.sh 的各步骤）</summary>

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

## 模型下载

`install.sh` 会自动下载。手动下载有两种方式：

```bash
# 方式一：ModelScope 命令行（推荐，支持断点续传）
pip install modelscope
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 \
    --local_dir CosyVoice/pretrained_models/Fun-CosyVoice3-0.5B

# 方式二：本仓库脚本（逐文件下载 + 远端大小校验，更抗中断）
python scripts/download_model.py
```

模型放在任意路径都可以，合成时用 `--model-dir` 指定：

```bash
modelscope download --model FunAudioLLM/Fun-CosyVoice3-0.5B-2512 --local_dir /your/model/path

TEXT_ECHO_DEVICE=cpu python scripts/tts_cv3.py --model-dir /your/model/path \
    --ref your_ref.m4a --prompt-text "参考音频里说的原话" --text "目标文字" --out result.wav
```

## 快速开始

```bash
conda activate cosyvoice

# zero-shot 克隆（推荐）：参考音频 + 它的原话 + 目标文字
TEXT_ECHO_DEVICE=cpu python scripts/tts_cv3.py \
    --ref your_ref.m4a \
    --prompt-text "参考音频里说的原话" \
    --text "要合成的目标文字" \
    --out result.wav

# cross-lingual 模式：免参考文字，不吃听写错误
TEXT_ECHO_DEVICE=cpu python scripts/tts_cv3.py \
    --ref your_ref.m4a \
    --text "要合成的目标文字" \
    --no-prompt-text \
    --out result.wav
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `TEXT_ECHO_DEVICE=cpu\|mps` | 推理设备（MPS 需 `PYTORCH_ENABLE_MPS_FALLBACK=1`） |
| `--rl` | 用 RL 强化学习权重（韵律更自然，实测推荐） |
| `--clip-seconds N` | 参考音频取前 N 秒（5~10 最佳；0=不截取） |
| `--no-denoise` | 清洗时不降噪（人声干净时用，避免发闷） |
| `--no-clean` | 完全关闭参考音频清洗 |

### 效果经验（实测）

1. **克隆相似度 ~70% 由参考音频质量决定**：单人、无背景音乐、吐字清楚、纯一种语言、5~10 秒、情绪平稳。
2. **RL 权重（`--rl`）优于 base**：韵律更自然。
3. **参考文字必须与录音一字不差**；听不准就用 cross-lingual 模式绕开。
4. 合成文本长度最好 ≥ 参考文字的一半，过短会触发模型警告。
5. 模型原生输出 24kHz，脚本自动输出润色版（loudnorm + 44.1kHz）。

## 目录结构

```
Cosyvoice3-mac/
├── README.md
├── install.sh              # 幂等一键部署
├── environment.yml         # conda 环境定义（py3.10 + pynini + ffmpeg）
├── requirements.mac.txt    # L0 最小依赖清单（每行带理由注释）
├── patches/
│   ├── README.md
│   └── 0001-macos-mps-device.patch   # 对上游 CosyVoice 的 MPS 补丁
├── scripts/
│   ├── tts_cv3.py          # 日常合成 CLI（清洗管线 + 两模式 + RL）
│   ├── smoke_cv3.py        # 快速实验/A-B 对比
│   └── download_model.py   # ModelScope 逐文件下载 + 校验（断点续传）
└── CosyVoice/              # install.sh 自动拉取的上游源码 + 模型（不入库）
```

## MPS 补丁说明

官方代码设备逻辑写死 `cuda else cpu`，Mac 上会静默跑 CPU。`patches/0001-macos-mps-device.patch` 修改：

- `cosyvoice/cli/model.py`：`get_device()`（cuda→MPS→cpu，支持 `TEXT_ECHO_DEVICE` 覆盖）、设备无关 autocast、`torch.mps.empty_cache()`
- `cosyvoice/hifigan/generator.py`：MPS 不支持 float64，f0 预测回 CPU（官方注释建议的做法）

上游代码不入库，升级后重新 `git apply` 即可。

## 踩坑记录

按官方流程在 Mac 上部署必踩的坑，`install.sh` 已全部自动处理：

| # | 现象 | 根因 | 解法 |
|---|---|---|---|
| 1 | `pynini` pip 安装编译失败 | 需编译 C++ 的 OpenFst | conda-forge 安装预编译包 |
| 2 | `requirements.txt` 报错/拖慢 | 首行 CUDA pip 源（cu121） | 用本仓库的 `requirements.mac.txt` |
| 3 | `openai-whisper` 报 `No module named 'pkg_resources'` | setuptools≥81 移除了它 | 装 `setuptools<81` |
| 4 | `pyworld` 编译报缺 numpy | 构建隔离环境不带 numpy | 先装 `numpy==1.26.4` 再 `--no-build-isolation` |
| 5 | Matcha-TTS 子模块为空 → yaml 加载报 `No module named 'matcha'` | clone 时没拉子模块 | `git clone --recursive` |
| 6 | 推理报缺 `llm.pt` / `speech_tokenizer_v3.onnx` | 大文件下载被中断 | 重跑 `scripts/download_model.py`（逐文件断点续传 + 远端大小校验） |
| 7 | `snapshot_download` 中断后目录被清空/损坏 | local_dir 同步模式在异常中断后不可靠 | 同上：逐文件 API 下载 |
| 8 | CosyVoice3 报 `<|endofprompt|> not detected` | v3 要求文本显式携带该特殊 token | 脚本已自动补 `You are a helpful assistant.<|endofprompt|>` 前缀 |
| 9 | `ModuleNotFoundError`（diffusers/lightning/librosa 等） | 被 yaml/子模块间接 import，静态分析扫不到 | 本仓库 `requirements.mac.txt` 已含全部实测依赖 |

依赖最小化思路：只装推理必需包（训练/webui 的依赖不装），每行注明用途；conda 层负责难编译的 pynini 和 ffmpeg，pip 层钉死实测版本组合。

## ⚠️ 合规提醒

语音克隆仅用于：**你自己的声音** / **已获明确授权的声音** / 模型自带默认音色。不要克隆影视角色、特定艺人或他人的声线用于欺骗或商用（声音权、肖像权、IP 授权风险）。

## 致谢

- [CosyVoice / Fun-CosyVoice3](https://github.com/FunAudioLLM/CosyVoice) by FunAudioLLM / 阿里通义实验室（Apache-2.0）
- [cosyvoice2-mac](https://github.com/BreetyGreen/cosyvoice2-mac)（MIT）——环境踩坑方案的起点
- 模型权重：[ModelScope: FunAudioLLM/Fun-CosyVoice3-0.5B-2512](https://www.modelscope.cn/models/FunAudioLLM/Fun-CosyVoice3-0.5B-2512)

## License

MIT（见 [LICENSE](LICENSE)）；上游 CosyVoice 为 Apache-2.0。

---

<a name="english"></a>
## English

Cosyvoice3-mac runs **Fun-CosyVoice3-0.5B** (zero-shot voice-cloning TTS) locally on **Apple Silicon Macs**. It adapts the deployment know-how of [cosyvoice2-mac](https://github.com/BreetyGreen/cosyvoice2-mac) to CosyVoice3 with: an MPS device patch (`patches/`), a minimal dependency set installable entirely from CN mirrors, an idempotent installer, reference-audio cleaning, and optional RL weights. See the 中文 sections above. Voice cloning only with your own voice or explicit consent — see the compliance notice.
