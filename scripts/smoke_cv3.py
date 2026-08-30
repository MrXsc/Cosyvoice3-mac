#!/usr/bin/env python
"""M1/M2 冒烟测试：验证环境/模型/补丁全链路。

默认：官方自带参考音频 + cross-lingual 模式（验证管道用）。
--ref 指定自己的音频时切换到 zero-shot 模式（需要 --prompt-text，
不给则用 whisper 自动识别）。

用法（在仓库根目录）：
  TEXT_ECHO_DEVICE=cpu python scripts/smoke_cv3.py
  TEXT_ECHO_DEVICE=cpu python scripts/smoke_cv3.py --ref my_ref.m4a --prompt-text "录音里说的话"
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COSYVOICE_DIR = os.path.join(REPO_ROOT, "CosyVoice")
ORIG_CWD = os.getcwd()  # 用户启动时的目录（--ref 相对路径以它为基准）
os.chdir(COSYVOICE_DIR)
sys.path.insert(0, COSYVOICE_DIR)
sys.path.insert(0, os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS"))

# 用绝对路径调 python 时 conda 环境的 bin 不在 PATH，ffmpeg 优先从当前解释器同目录找
FFMPEG = shutil.which("ffmpeg") or os.path.join(os.path.dirname(sys.executable), "ffmpeg")
# whisper 内部也 shell 调 ffmpeg，补进 PATH
os.environ["PATH"] = os.path.dirname(FFMPEG) + os.pathsep + os.environ.get("PATH", "")

import torch  # noqa: E402
import torchaudio  # noqa: E402
from cosyvoice.cli.cosyvoice import AutoModel  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--ref", default=None, help="自己的参考音频；不给则用官方 cross_lingual_prompt.wav")
ap.add_argument("--prompt-text", default=None, help="参考音频对应文字（zero-shot）；不给则 whisper 识别")
ap.add_argument("--text", default="You are a helpful assistant.<|endofprompt|>你好，欢迎来到语音合成测试。",
                help="要合成的目标文字")
ap.add_argument("--clip-seconds", type=float, default=8.0, help="参考音频取前 N 秒")
ap.add_argument("--rl", action="store_true", help="用 llm.rl.pt（强化学习权重）替代 base llm.pt")
ap.add_argument("--tag", default="", help="输出文件名附加标记")
ap.add_argument("--cross-lingual", action="store_true",
                help="配合 --ref：用 cross-lingual 模式（免参考文字，跳过 whisper）")
ap.add_argument("--no-denoise", action="store_true", help="清洗时不做降噪（人声干净、降噪后发闷时用）")
args = ap.parse_args()

device = os.environ.get("TEXT_ECHO_DEVICE", "cpu")
print(f">>> 设备: {device}（torch {torch.__version__}）")
print(">>> 模型加载中（首次 1~2 分钟）...")
t0 = time.time()
model = AutoModel(model_dir="pretrained_models/Fun-CosyVoice3-0.5B", fp16=False)
if args.rl:
    # 用 RL 权重替换 base llm（与 CosyVoice3Model.load 同样的加载方式）
    rl_path = "pretrained_models/Fun-CosyVoice3-0.5B/llm.rl.pt"
    assert os.path.isfile(rl_path), f"{rl_path} 不存在"
    import torch as _t
    state = _t.load(rl_path, map_location=model.model.device, weights_only=True)
    model.model.llm.load_state_dict(state, strict=True)
    model.model.llm.to(model.model.device).eval()
    print(">>> 已加载 RL 权重 llm.rl.pt")
print(f">>> 模型加载 {time.time() - t0:.1f}s")

tag = "smoke"
if args.ref:
    # 参考音频清洗（与 tts_cv3 同一管线）后走 zero-shot
    ref = os.path.abspath(os.path.expanduser(args.ref)) if os.path.isabs(args.ref) \
        else os.path.abspath(os.path.join(ORIG_CWD, os.path.expanduser(args.ref)))
    prompt_wav = os.path.join(COSYVOICE_DIR, "_ref_16k.wav")
    subprocess_ffmpeg = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", ref,
        "-af", "aformat=channel_layouts=mono,highpass=f=80,"
               + ("" if args.no_denoise else "afftdn=nf=-25,")
               + "loudnorm=I=-16:TP=-1.5:LRA=11,"
               "silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB:"
               "stop_periods=-1:stop_silence=0.5:stop_threshold=-45dB",
        "-ar", "16000", "-ac", "1",
    ]
    if args.clip_seconds > 0:
        subprocess_ffmpeg += ["-t", f"{args.clip_seconds:.2f}"]
    subprocess_ffmpeg.append(prompt_wav)
    r = subprocess.run(subprocess_ffmpeg, capture_output=True)
    if r.returncode != 0:
        sys.exit("ffmpeg 清洗失败:\n" + r.stderr.decode("utf-8", "ignore")[-800:])
    print(f">>> 参考音频已清洗: {prompt_wav}")

    prompt_text = None
    if not args.cross_lingual:
        prompt_text = args.prompt_text
        if not prompt_text:
            import whisper
            print(">>> whisper 识别参考文字...")
            prompt_text = whisper.load_model("small").transcribe(
                prompt_wav, language="zh", fp16=False)["text"].strip()
            print(f">>> 参考文字：{prompt_text}")
        # CosyVoice3 zero-shot：参考文字需携带 <|endofprompt|>（llm.py 硬校验）
        if "<|endofprompt|>" not in prompt_text:
            prompt_text = "You are a helpful assistant.<|endofprompt|>" + prompt_text
    tag = "crosslingual" if args.cross_lingual else "zero_shot"
    if args.cross_lingual and "<|endofprompt|>" not in args.text:
        # cross-lingual 会移除参考文字，<|endofprompt|> 必须在合成文本里
        args.text = "You are a helpful assistant.<|endofprompt|>" + args.text
    tag += "_" + os.path.splitext(os.path.basename(args.ref))[0] \
        + ("_rl" if args.rl else "") + (f"_{args.tag}" if args.tag else "")

    def gen():
        if args.cross_lingual:
            return model.inference_cross_lingual(args.text, prompt_wav, stream=False)
        return model.inference_zero_shot(args.text, prompt_text, prompt_wav, stream=False)
else:
    tag = "smoke" + ("_rl" if args.rl else "") + (f"_{args.tag}" if args.tag else "")

    def gen():
        return model.inference_cross_lingual(args.text, "asset/cross_lingual_prompt.wav", stream=False)

t1 = time.time()
out = os.path.join(REPO_ROOT, f"{tag}_{device}.wav")
for i, chunk in enumerate(gen()):
    target = out if i == 0 else f"{out}.{i}.wav"
    torchaudio.save(target, chunk["tts_speech"], model.sample_rate)
    # 输出后处理：响度归一化 + 重采样 44.1kHz（模型原生 24kHz，改善听感电平）
    polished = target.replace(".wav", "_polished.wav")
    import subprocess as _sp
    r = _sp.run([FFMPEG, "-y", "-v", "error", "-i", target,
                 "-af", "loudnorm=I=-14:TP=-1.0:LRA=9", "-ar", "44100", polished],
                capture_output=True)
    if r.returncode == 0:
        print(f"✅ {target}  时长 {chunk['tts_speech'].shape[1] / model.sample_rate:.1f}s  (+ 润色版 {os.path.basename(polished)})")
    else:
        print(f"✅ {target}  时长 {chunk['tts_speech'].shape[1] / model.sample_rate:.1f}s  (润色失败，保留原版)")
print(f"🎉 合成完成（{device}），耗时 {time.time() - t1:.1f}s，采样率 {model.sample_rate}")
