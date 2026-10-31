# Angel Sex Pet — PS Vita 移植

把 Cherry Kiss Games 的 Ren'Py 游戏《Angel Sex Pet》(聖天使シャーロット) 移植到
PS Vita 的完整方案。

**本仓库不含游戏本体。** 请自行购买正版，用自己机器上的游戏数据按下面步骤打包。

---

## 状态

| 项 | 结果 |
|---|---|
| 真机运行 | ✅ PS Vita 3.65 变革（Enso），Ren'Py 7.4.9 运行时 |
| 游戏版本 | Ren'Py 7.3.5 |
| 进游戏 | ✅ 主菜单、剧情、存档全部正常 |
| 打包体积 | 298 MB → 194.5 MB（降采样后） |

---

## 这个游戏有三个坑，缺一个都起不来

按踩坑顺序：

### 坑 1｜运行时缺预编译脚本

Distribution Tool 自带的 `renpy/common` 里**一个 `.rpyc` 都没有**，只有 `.rpy`。
`app0:` 是只读挂载，Ren'Py 写不回编译产物，于是每次启动都要在 Vita 上
现场编译 54 个脚本 —— 表现为卡在启动图几分钟然后崩溃。

**修法**：从一个能跑的 Vita 移植包里整目录复制 `renpy/common`（336 个文件，
含 54 个 `.rpyc`）。

### 坑 2｜`script_version.txt` 被汉化组塞了水印

```
(7, 3, 5)\r\n
\r\n
更多资源:SEEACG.COM      ← GBK 字节
```

Ren'Py 用 `ast.literal_eval` 读**整个文件**，多出来的中文行直接抛 `SyntaxError`，
而外面包着 `except: pass`。后果：

* 日志里永远不会出现 `Set script version to:`；
* `config.script_version` 保持 `None`，兼容层全部跳过。

**修法**：

```bash
python tools/fix_script_version.py <游戏目录> --write
```

### 坑 3｜游戏自带首发联网上报（真正的崩溃点）

反编译 `splashscreen.rpyc` 可以看到：

```python
init -3 python:
    persistent.jp_installed = False
    if not persistent.data_checked:
        import requests
        userdata = requests.get('http://ipinfo.io/json').json()
        useranalytics = requests.post('http://ent943y5tpj9hth.m.pipedream.net', data=userdata)
        persistent.jp_ipcountry = userdata['country']
        persistent.data_checked = True
```

发行商内嵌的遥测。Vita 的 `python27.zip` 里没有 `_ssl`、没有 certifi，
`app0:` 又只读 —— 未捕获异常直接把 init 阶段打死。

**修法**：加一个更高优先级的 init 块抢先把标志置位：

```python
init -10 python:
    persistent.data_checked = True
```

编译成 `psv_skip_telemetry.rpyc` 放进 `game/`。**必须用 Ren'Py SDK 编译**，
版本常量要是 5003000。

> 这个坑不止这一款游戏。实测 11 个 Cherry Kiss / Miel 系游戏都有同样的代码，
> 只是上报端点不同。

---

## 打包步骤

### 0. 准备

```bash
git clone <this-repo>
# 需要 Ren'Py 7.4.9 SDK（用来编译 .rpyc）
# https://www.renpy.org/dl/7.4.9/renpy-7.4.9-sdk.zip
```

把环境变量设为你的 SDK 路径：

```bash
export RENPY_SDK=/path/to/renpy-7.4.9-sdk
```

### 1. 准备游戏数据

把正版游戏的 `game/` 目录内容拷过来（`archive.rpa`、`img_resource.rpa`、
`gui_resource.rpa`、`sfx_resource.rpa`、`dlc_japanese.rpa`）。

### 2. 清掉 `script_version.txt` 的水印

```bash
python tools/fix_script_version.py ./game --write
# 期望输出：解析结果: (7, 3, 5)   干净=True
```

### 3. 生成跳过上报的补丁

```bash
python tools/fix_telemetry.py ./game --write --sdk "$RENPY_SDK"
# 产出 game/psv_skip_telemetry.rpyc （794 字节）
```

### 4. 降采样图片（可选，但强烈建议）

```bash
python tools/optimize_images.py game/img_resource.rpa game/img_opt.rpa --max-w 1366 --max-h 768
python tools/optimize_images.py game/gui_resource.rpa game/gui_opt.rpa --max-w 1366 --max-h 768
```

实测：144.5 MB → 42.3 MB，单张解码 83.6 ms → 19.4 ms。

### 5. 删掉用不到的翻译（可选）

```bash
python tools/rpa_tool.py filter game/archive.rpa game/archive_opt.rpa --drop 'tl/en/,tl/es/,tl/zhtw/'
```

启动时 5 套完整翻译都会被解析，删掉用不到的能省一半加载时间。

### 6. 应用性能配置

把 `patches/psv_perf.rpy` 放进 `game/`，用 SDK 编译：

```bash
cp patches/psv_perf.rpy ./game/
"$RENPY_SDK/renpy.exe" <临时项目路径> lint   # 产出 psv_perf.rpyc
rm ./game/psv_perf.rpy                       # 只留 .rpyc
```

或者直接用仓库里预编译好的 `patches/psv_perf.rpyc`。

### 7. 生成 sce_sys

```bash
python tools/make_scesys_generic.py ./sce_sys ./logo.png ./alt.png "Angel Sex Pet"
"$RENPY_SDK/../disttool/vita-mksfoex.exe" -s TITLE_ID=ANGE00001 \
    -d ATTRIBUTE2=12 -s APP_VER=01.00 "Angel Sex Pet" ./sce_sys/param.sfo
```

硬性规格（不符合就 `0x8010113D`）：

| 文件 | 尺寸 | 要求 |
|---|---|---|
| `icon0.png` | 128×128 | 8-bit 索引色，无 alpha |
| `pic0.png` | 960×544 | 8-bit 索引色，无 alpha |
| `livearea/contents/bg.png` | 840×500 | 8-bit 索引色，无 alpha |
| `livearea/contents/startup.png` | 280×158 | 8-bit 索引色，可有 alpha |

### 8. 装到 Vita

**推荐拆开装**：

1. 打一个只含运行时的 VPK（约 14 MB），VitaShell 安装 → 气泡和 `app.db` 记录都有了
2. 用 USB 把 `game/*.rpa` 直接拷到 `ux0:/app/ANGE00001/game/`

不要试图文件夹直拷注册气泡 —— 在 3.65 上验证过两次都失败。

### 9. 验证

读 `ux0:/app/ANGE00001/log.txt`，对照：

| log 行 | 含义 |
|---|---|
| `Set script version to: (7, 3, 5)` | 水印已清 |
| `Running init code took ...` | 上报块已跳过 |
| `Initializing gles renderer:` | 引擎起来了 |

---

## 目录结构

```
.
├── README.md
├── patches/
│   ├── psv_skip_telemetry.rpy    # 跳过上报的补丁源码
│   ├── psv_skip_telemetry.rpyc   # 预编译版（794 字节）
│   ├── psv_perf.rpy              # 性能配置
│   ├── psv_perf.rpyc             # 预编译版
│   ├── psv_input.rpy             # renpy.input 屏幕键盘（修改名卡死）
│   ├── psv_input.rpyc
│   ├── psv_keys.rpy              # ○ 确认 / × 返回
│   ├── psv_keys.rpyc
│   ├── psv_diag.rpy              # 性能探针（FRAME / TEXT / IMG / PAD）
│   └── psv_diag.rpyc
├── tools/
│   ├── fix_script_version.py
│   ├── fix_telemetry.py
│   ├── optimize_images.py
│   ├── jpeg_recompress.py
│   ├── rpa_tool.py
│   └── make_scesys_generic.py
└── docs/
    ├── 移植记录.md              # 完整踩坑过程
    └── 性能分析-文字渲染.md      # 卡顿根因分析与优化方向
```

---

## 已知问题

* 启动仍需约 40-70 秒（Vita 存储卡慢 + Ren'Py 要解 300 MB 的 rpa 索引）
* **操作卡顿：文字渲染曾是唯一瓶颈（占 89–99%），已修复** —— 字体改为整块读入内存，
  进设置整帧 **10.23s → 2.76s（3.7×）**。详见
  [docs/性能分析-文字渲染.md](docs/性能分析-文字渲染.md)
* 日文字体（16 MB）尚未子集化，首次使用有约 1.7s 停顿，见上述文档「方向 2」
* 游戏内首次显示某张 CG 时仍会有短暂停顿（解码），降采样后已大幅改善
* 视频播放不支持（renpy-vita 的已知限制）
* 退出游戏会崩（renpy-vita 的已知问题，不影响存档）

### 已优化项（实测）

| 项 | 结果 |
|---|---|
| 素材降采样 + 转 JPEG | img 137.8 MB → 9.6 MB，gui 54.5 MB → 14.2 MB |
| CJK 字体子集化 | 3 × 17 MB → 3 × 4.1 MB |
| 删无用翻译 | 启动快约 20 秒 |
| `renpy.input` 屏幕键盘 | 修掉改名卡死 |
| 按键映射 | ○ 确认 / × 返回（PS 系习惯） |
| **字体整块读入内存** | **进设置整帧 10.23s → 2.76s（3.7×）** |

---

## 感谢

* [SonicMastr/renpy-vita](https://github.com/SonicMastr/renpy-vita) — Ren'Py 7 / Python 2.7 运行时
* [CensoredUsername/unrpyc](https://github.com/CensoredUsername/unrpyc) — .rpyc 反编译器
* [GrapheneCt/PVR_PSP2](https://github.com/GrapheneCt/PVR_PSP2) — PowerVR 驱动

## 许可

本仓库的脚本和补丁以 MIT 许可发布。游戏本体版权归 Cherry Kiss Games 所有。
