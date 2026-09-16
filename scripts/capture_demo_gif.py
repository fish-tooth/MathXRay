"""Capture MathXRay slides and app demo pages into demo/mathxray.gif.

Requires a running app:  streamlit run app.py
Optional:               pip install selenium
"""

from __future__ import annotations

import argparse
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
HIDE_CSS = """
[data-testid="stHeader"], header[data-testid="stHeader"],
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton,
[data-testid="stSidebar"], [data-testid="collapsedControl"],
footer, #MainMenu { display: none !important; }
[data-testid="stAppViewContainer"] { max-width: 100% !important; }
section.main, [data-testid="stMain"] { margin: 0 !important; }
.block-container { max-width: 1080px !important; padding-top: 0.45rem !important; padding-bottom: 0.4rem !important; }
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
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=0", "割草机", None),
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=1", "长方形", ".step.invalid"),
    ("/?embed=true&page=solve&demo_engine=r1&demo_case=2", "共线", ".warn-banner"),
    ("/?embed=true&page=dashboard", "评测看板", None),
]

DURATIONS_MS = [2400] * len(STORY_NEEDLES) + [3200, 3400, 3400, 3000]
for i in (14, 15, 16, 20, 21, 22):
    if i < len(STORY_NEEDLES):
        DURATIONS_MS[i] = 3200


def _driver(width: int, height: int) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument("--force-device-scale-factor=1")
    opts.add_argument(f"--window-size={width},{height}")
    opts.add_argument("--lang=zh-CN")
    driver = webdriver.Chrome(options=opts)
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


def capture(base: str, width: int, height: int) -> list[Path]:
    driver = _driver(width, height)
    paths: list[Path] = []
    try:
        for i, needle in enumerate(STORY_NEEDLES):
            driver.get(f"{base}/?embed=true&page=story&slide={i}")
            _prepare(driver, needle)
            paths.append(_shot(driver, f"{i:02d}_story.png"))
        for j, (path, needle, scroll) in enumerate(APP_PAGES):
            print(f"app {j} {needle}")
            driver.get(base.rstrip("/") + path)
            _prepare(driver, needle)
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
        im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.Resampling.LANCZOS)
        if im.size[1] > h:
            im = im.crop((0, 0, w, h))
        elif im.size[1] < h:
            canvas = Image.new("RGB", size, (247, 248, 251))
            canvas.paste(im, (0, 0))
            im = canvas
    return im


def compose_gif(frame_paths: list[Path], width: int, height: int) -> Path:
    images = [_normalize(p, (width, height)) for p in frame_paths]
    palette_src = images[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    paletted = [im.quantize(palette=palette_src) for im in images]
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8501")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    args = parser.parse_args()
    frames = capture(args.base.rstrip("/"), args.width, args.height)
    out = compose_gif(frames, args.width, args.height)
    print(f"frames={len(frames)} gif={out} size={out.stat().st_size}")


if __name__ == "__main__":
    main()
