#!/usr/bin/env python3
"""一键把 Angel Sex Pet 打包成 PS Vita 可安装的 VPK / NoNpDrm 包。

前提：
  * 你有正版游戏（Steam 版），已购买
  * 有 Ren'Py 7.4.9 SDK（用来编译补丁 .rpyc）
  * 有 renpy-vita 运行时目录（eboot.bin / renpy.py / lib / module / renpy/common）

用法：

  # 完整流程（优化 + 打包）
  python build.py --game "C:/path/to/AngelSexPet/game" \
                  --runtime "C:/path/to/runtime" \
                  --sdk "C:/path/to/renpy-7.4.9-sdk" \
                  --out dist

  # 跳过素材优化（想保留原始画质）
  python build.py ... --no-optimize

产出：
  dist/AngelSexPet_Runtime.vpk   只含运行时（14 MB）
  dist/AngelSexPet_Full.vpk      运行时 + 游戏数据（约 125 MB）
  dist/AngelSexPet_NoNpDrm.zip   同上，文件夹形式
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, "tools")


def run(cmd):
    print("  $ " + " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("命令失败: %s" % " ".join(cmd))


def main():
    args = sys.argv[1:]

    def arg(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    game = arg("--game")
    runtime = arg("--runtime")
    sdk = arg("--sdk")
    out = arg("--out", os.path.join(HERE, "dist"))
    title_id = arg("--title-id", "ANGE00001")
    optimize = "--no-optimize" not in args

    if not game or not runtime:
        print(__doc__)
        return 1

    work = os.path.join(HERE, "work")
    os.makedirs(work, exist_ok=True)

    # ---------- 1) 修 script_version 水印 ----------
    print("\n[1/6] 清理 script_version.txt")
    subprocess.run([sys.executable, os.path.join(TOOLS, "fix_script_version.py"),
                    game, "--write"])

    # ---------- 2) 采集 game 数据 ----------
    print("\n[2/6] 收集游戏数据")
    g = os.path.join(work, "game")
    if os.path.isdir(g):
        shutil.rmtree(g)
    os.makedirs(g)
    for n in os.listdir(game):
        p = os.path.join(game, n)
        if os.path.isfile(p) and n.lower().endswith((".rpa", ".rpyc", ".txt")):
            shutil.copy2(p, os.path.join(g, n))
    print("  %d 个文件" % len(os.listdir(g)))

    # ---------- 3) 素材优化 ----------
    if optimize:
        print("\n[3/6] 素材优化")
        for name in list(os.listdir(g)):
            if not name.endswith(".rpa"):
                continue
            src = os.path.join(g, name)
            step1 = os.path.join(work, name + ".s1")
            step2 = os.path.join(work, name + ".s2")
            print("  -- %s 降采样" % name)
            run([sys.executable, os.path.join(TOOLS, "optimize_images.py"),
                 src, step1, "--max-w", "1366", "--max-h", "768"])
            print("  -- %s 转 JPEG" % name)
            run([sys.executable, os.path.join(TOOLS, "jpeg_recompress.py"),
                 step1, step2, "--quality", "85"])
            os.replace(step2, src)
            for t in (step1,):
                if os.path.exists(t):
                    os.remove(t)
    else:
        print("\n[3/6] 跳过素材优化")

    # ---------- 4) 生成补丁 ----------
    print("\n[4/6] 生成补丁")
    if sdk:
        run([sys.executable, os.path.join(TOOLS, "fix_telemetry.py"),
             g, "--write", "--sdk", sdk])
    else:
        print("  !! 没给 --sdk，跳过补丁生成（会崩）")
    for patch in ("psv_skip_telemetry.rpyc", "psv_perf.rpyc"):
        p = os.path.join(HERE, "patches", patch)
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(g, patch))
            print("  已加入 %s" % patch)

    # ---------- 5) 打包 ----------
    print("\n[5/6] 打包")
    run([sys.executable, os.path.join(TOOLS, "build_package.py"),
         "--build", runtime, "--game", g, "--out", out,
         "--title-id", title_id])

    # ---------- 6) 完成 ----------
    print("\n[6/6] 完成，产物在 %s" % out)
    for n in sorted(os.listdir(out)):
        if n.endswith((".vpk", ".zip")):
            print("  %-34s %6.1f MB" % (n, os.path.getsize(os.path.join(out, n)) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
