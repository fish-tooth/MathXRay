"""Capture MathXRay slides and app demo pages into demo/mathxray.gif.

Requires a running app:  streamlit run app.py
Optional:               pip install selenium
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
FRAMES = DEMO_DIR / "frames"
GIF_PATH = DEMO_DIR / "mathxray.gif"
PLAYER_PATH = DEMO_DIR / "player.html"
MANIFEST_PATH = FRAMES / "manifest.js"
HIDE_CSS = """
[data-testid="stHeader"], header[data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton,
[data-testid="stSidebar"], [data-testid="collapsedControl"],
footer, #MainMenu { display: none !important; }
[data-testid="stAppViewContainer"] { max-width: 100% !important; }
section.main, [data-testid="stMain"] { margin: 0 !important; }
.block-container { max-width: 1320px !important; padding-top: 0.4rem !important; padding-bottom: 0.35rem !important; }
.stButton, [data-testid="stButton"], [data-testid="stCaptionContainer"] { display: none !important; }
"""

STORY_NEEDLES = [
    "过程审查看什么",
    "只看答案会漏掉什么",
    "从解题到出报告",
    "审查结果里有什么",
    "一次看完就给结论",
    "把审查拆成四段",
    "先自己做一遍",
    "每一段单独判断",
    "错从哪一步进来",
    "形式还不完整",
    "什么时候才对质",
    "指控、辩护、仲裁",
    "汇总按固定顺序",
    "应用里怎么查看",
    "过程成立的例子",
    "中间一步算错",
    "答案对了，过程不完整",
    "题越难，指出首错越吃力",
    "各数据集对照",
    "私有高中题，只在本地使用",
    "同一 88 道题上的对照",
    "四项对照",
    "28 道是怎么判出来的",
    "这些数字分别在说什么",
    "这套设计好在哪",
    "目前的限制",
    "下一步",
]

APP_PAGES = [
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=0", "割草机", None, "过程对了的例子"),
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=1", "长方形", ".step.invalid", "中间一步算错"),
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=2", "共线", ".warn-banner", "答案对了，过程不完整"),
    ("/?embed=true&page=dashboard", "评测看板", None, "评测看板"),
]

DURATIONS_MS = [2400] * len(STORY_NEEDLES) + [3200, 3400, 3400, 3000]
for i in (14, 15, 16, 20, 21, 22):
    if i < len(STORY_NEEDLES):
        DURATIONS_MS[i] = 3200


def _driver(width: int, height: int, dpr: float) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--force-color-profile=srgb")
    opts.add_argument("--font-render-hinting=none")
    opts.add_argument(f"--force-device-scale-factor={dpr}")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--lang=zh-CN")
    driver = webdriver.Chrome(options=opts)
    try:
        driver.execute_cdp_cmd(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": width,
                "height": height,
                "deviceScaleFactor": dpr,
                "mobile": False,
            },
        )
    except Exception:
        pass
    driver.set_window_size(width, height)
    return driver


def _prepare(driver: webdriver.Chrome, needle: str, timeout: float = 25.0) -> None:
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".slide-title, .mx-title"))
    )
    WebDriverWait(driver, timeout).until(lambda d: needle in d.page_source)
    driver.execute_script(
        "let s=document.getElementById('demo-hide');"
        "if(!s){s=document.createElement('style');s.id='demo-hide';document.head.appendChild(s);}"
        "s.textContent=arguments[0];",
        HIDE_CSS,
    )
    time.sleep(0.7)


def _shot(driver: webdriver.Chrome, name: str) -> Path:
    FRAMES.mkdir(parents=True, exist_ok=True)
    path = FRAMES / name
    driver.save_screenshot(str(path))
    return path


def capture(base: str, width: int, height: int, dpr: float) -> list[Path]:
    driver = _driver(width, height, dpr)
    paths: list[Path] = []
    try:
        for i, needle in enumerate(STORY_NEEDLES):
            driver.get(f"{base}/?embed=true&capture=1&page=story&slide={i}")
            _prepare(driver, needle)
            paths.append(_shot(driver, f"{i:02d}_story.png"))
        for j, (path, needle, scroll, _title) in enumerate(APP_PAGES):
            print(f"app {j} {needle}")
            driver.get(base.rstrip("/") + path)
            _prepare(driver, needle)
            if needle == "评测看板":
                time.sleep(1.2)
            if scroll:
                driver.execute_script(
                    "const e=document.querySelector(arguments[0]);"
                    "if(e) e.scrollIntoView({block:'center'});",
                    scroll,
                )
                time.sleep(0.35)
            paths.append(_shot(driver, f"{len(STORY_NEEDLES) + j:02d}_app.png"))
    finally:
        driver.quit()
    return paths


def _normalize(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    w, h = size
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    im.save(path, format="PNG", optimize=True)
    return im


def compose_gif(frame_paths: list[Path], width: int, height: int) -> Path:
    images = [_normalize(p, (width, height)) for p in frame_paths]
    palette_src = images[0].quantize(colors=256, method=Image.Quantize.MAXCOVERAGE)
    paletted = [
        im.quantize(palette=palette_src, dither=Image.Dither.NONE) for im in images
    ]
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    paletted[0].save(
        GIF_PATH,
        save_all=True,
        append_images=paletted[1:],
        duration=DURATIONS_MS[: len(paletted)],
        loop=0,
        optimize=False,
        disposal=2,
    )
    return GIF_PATH


def write_manifest(frame_paths: list[Path]) -> None:
    titles = list(STORY_NEEDLES) + [item[3] for item in APP_PAGES]
    frames = []
    for i, path in enumerate(frame_paths):
        frames.append(
            {
                "src": f"frames/{path.name}",
                "ms": int(DURATIONS_MS[i] if i < len(DURATIONS_MS) else 2800),
                "title": titles[i] if i < len(titles) else path.stem,
            }
        )
    FRAMES.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"frames": frames}, ensure_ascii=False, indent=2)
    MANIFEST_PATH.write_text(f"window.MX_DEMO = {payload};\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8501")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--dpr", type=float, default=2.0)
    args = parser.parse_args()
    frames = capture(args.base.rstrip("/"), args.width, args.height, args.dpr)
    write_manifest(frames)
    out = compose_gif(frames, args.width, args.height)
    print(f"frames={len(frames)} gif={out} size={out.stat().st_size} player={PLAYER_PATH}")


if __name__ == "__main__":
    main()
