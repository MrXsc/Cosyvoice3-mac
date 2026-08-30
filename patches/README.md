# 对上游 CosyVoice 的补丁

上游源码不入库（`.gitignore` 排除 `CosyVoice/`）。所有对官方代码的修改都以 patch 文件保存，
官方代码升级后可重新套用：

```bash
cd CosyVoice
git checkout -- .            # 还原上游代码
git apply ../patches/0001-macos-mps-device.patch
```

## 0001-macos-mps-device.patch

`cosyvoice/cli/model.py`：
- 新增 `get_device()`：cuda → MPS → cpu（支持 `TEXT_ECHO_DEVICE=mps|cpu` 强制指定，对比测试用）
- 新增 `_autocast_ctx()`：官方 `torch.cuda.amp.autocast` 只认 cuda，改为设备无关写法
- 新增 `_empty_cache()`：MPS 下走 `torch.mps.empty_cache()`
- 三处设备选择 / 三处 llm_context / 四处 autocast / 两处缓存清理全部替换
