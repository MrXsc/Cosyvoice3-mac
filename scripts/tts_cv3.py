#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tts_cv3.py — Fun-CosyVoice3-0.5B 音色克隆命令行工具（macOS）。

移植自 cosyvoice2-mac/tts.py 的骨架（参考音频清洗管线、参数约定），
入口换成 CosyVoice3 的 AutoModel；设备补丁见 patches/。

用法：
  # cross-lingual（推荐脏音频，免听写）
  python tts_cv3.py --ref ref.wav --text "要合成的文字" --no-prompt-text

  # zero-shot（自动 whisper 听写，需 L1 层装 whisper）
  python tts_cv3.py --ref ref.wav --prompt-text "参考音频说的话" --text "..."
"""
import argparse
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COSYVOICE_DIR = os.path.join(REPO_ROOT, "CosyVoice")
MODEL_DIR = "pretrained_models/Fun-CosyVoice3-0.5B"


def _run_ffmpeg(args):
    # 用绝对路径调 python 时 conda 环境的 bin 不在 PATH，ffmpeg 优先从当前解释器同目录找
    import shutil
    ffmpeg = shutil.which("ffmpeg") or os.path.join(os.path.dirname(sys.executable), "ffmpeg")
    proc = subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *args],
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg 失败:\n" + proc.stderr.decode("utf-8", "ignore")[-800:])


def _probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().strip()
        return float(out)
    except Exception:
        return 0.0


def preprocess_audio(src, dst, clip_seconds=0.0, denoise=True):
    """参考音频清洗管线（克隆相似度 ~70% 由参考音频决定）：
    单声道 → 高通去低频 → FFT降噪 → 响度归一化 → 切静音 → 16k。"""
    chain = ["aformat=channel_layouts=mono", "highpass=f=80"]
    if denoise:
        chain.append("afftdn=nf=-25")
    chain.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    chain.append("silenceremove=start_periods=1:start_silence=0.1:start_threshold=-45dB:"
                 "stop_periods=-1:stop_silence=0.5:stop_threshold=-45dB")
    args = ["-i", src, "-af", ",".join(chain), "-ar", "16000", "-ac", "1"]
    if clip_seconds > 0:
        args += ["-t", f"{clip_seconds:.2f}"]
    args.append(dst)
    _run_ffmpeg(args)
    dur = _probe_duration(dst)
    print(f">>> 清洗完成：{dur:.1f}s（降噪={'开' if denoise else '关'}）")
    if dur < 2.0:
        print("⚠️ 清洗后不足 2 秒，可试 --no-clean")
    return dst


def transcribe(wav, lang="zh"):
    import whisper
    print(">>> whisper 识别参考文字（首次会下载模型）...")
    model = whisper.load_model("small")
    text = model.transcribe(wav, language=lang, fp16=False)["text"].strip()
    print(f">>> 参考文字：{text}")
    return text


def main():
    ap = argparse.ArgumentParser(description="Fun-CosyVoice3 音色克隆")
    ap.add_argument("--ref", required=True, help="参考音频（wav/mp3）")
    ap.add_argument("--text", required=True, help="目标文字")
    ap.add_argument("--prompt-text", default=None, help="参考音频对应文字（zero-shot）")
    ap.add_argument("--no-prompt-text", action="store_true", help="cross-lingual 模式，免参考文字")
    ap.add_argument("--no-clean", action="store_true", help="关闭参考音频清洗")
    ap.add_argument("--no-denoise", action="store_true", help="清洗时不降噪")
    ap.add_argument("--clip-seconds", type=float, default=0.0, help="取清洗后前 N 秒（5~10 最佳）")
    ap.add_argument("--model-dir", default=os.path.join(COSYVOICE_DIR, MODEL_DIR))
    ap.add_argument("--device", default=None, choices=[None, "cpu", "mps"],
                    help="强制设备；默认由环境变量 TEXT_ECHO_DEVICE 决定（mps/cpu）")
    ap.add_argument("--out", default="output.wav")
    args = ap.parse_args()

    os.chdir(COSYVOICE_DIR)
    sys.path.insert(0, COSYVOICE_DIR)
    sys.path.insert(0, os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS"))

    if args.device:
        os.environ["TEXT_ECHO_DEVICE"] = args.device

    ref = os.path.abspath(os.path.expanduser(args.ref))
    if not os.path.isfile(ref):
        sys.exit(f"参考音频不存在：{ref}")

    prompt_wav = os.path.join(COSYVOICE_DIR, "_ref_16k.wav")
    if args.no_clean:
        _run_ffmpeg(["-i", ref, "-ar", "16000", "-ac", "1", prompt_wav])
    else:
        preprocess_audio(ref, prompt_wav, args.clip_seconds, not args.no_denoise)

    prompt_text = None
    if not args.no_prompt_text:
        prompt_text = args.prompt_text or transcribe(prompt_wav)

    # CosyVoice3 要求文本携带 <|endofprompt|> 特殊 token（llm.py 硬校验）：
    # zero-shot 放参考文字前，cross-lingual 放合成文本前（参照官方 example.py）
    PREFIX = "You are a helpful assistant.<|endofprompt|>"
    if "<|endofprompt|>" not in (prompt_text or args.text):
        if args.no_prompt_text:
            args.text = PREFIX + args.text
        else:
            prompt_text = PREFIX + prompt_text

    import torch
    import torchaudio
    from cosyvoice.cli.cosyvoice import AutoModel

    print(">>> 加载 CosyVoice3 模型（首次较慢）...")
    t0 = time.time()
    # fp16=False：MPS 上 fp16 数值不稳，先 fp32 跑通（WIKI §4.3）
    model = AutoModel(model_dir=args.model_dir, fp16=False)
    print(f">>> 模型加载 {time.time()-t0:.1f}s")
    gen = model.inference_cross_lingual(args.text, prompt_wav, stream=False) \
        if args.no_prompt_text else \
        model.inference_zero_shot(args.text, prompt_text, prompt_wav, stream=False)

    out_abs = os.path.abspath(os.path.expanduser(args.out))
    for i, chunk in enumerate(gen):
        target = out_abs if i == 0 else f"{out_abs}.{i}.wav"
        torchaudio.save(target, chunk["tts_speech"], model.sample_rate)
        print(f"✅ 已保存：{target}")
    print("🎉 完成")


if __name__ == "__main__":
    main()
