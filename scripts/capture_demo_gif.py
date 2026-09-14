"""Capture MathXRay Streamlit scenes into demo/mathxray.gif.

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
.block-container { max-width: 1040px !important; padding-top: 1.1rem !important; }
"""


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
        EC.presence_of_element_located((By.CSS_SELECTOR, ".mx-title"))
    )
    WebDriverWait(driver, timeout).until(lambda d: needle in d.page_source)
    driver.execute_script(
        "let s=document.getElementById('demo-hide');"
        "if(!s){s=document.createElement('style');s.id='demo-hide';document.head.appendChild(s);}"
        "s.textContent=arguments[0];",
        HIDE_CSS,
    )
    time.sleep(1.15)


def _shot(driver: webdriver.Chrome, name: str) -> Path:
    FRAMES.mkdir(parents=True, exist_ok=True)
    path = FRAMES / name
    driver.save_screenshot(str(path))
    return path


def _scroll_to(driver: webdriver.Chrome, selector: str) -> None:
    driver.execute_script(
        """
        const el = document.querySelector(arguments[0]);
        if (!el) return;
        el.scrollIntoView({block: 'center', inline: 'nearest'});
        const parents = [];
        let n = el.parentElement;
        while (n) { parents.push(n); n = n.parentElement; }
        for (const p of parents) {
          const cs = getComputedStyle(p);
          if (/(auto|scroll)/.test(cs.overflowY) && p.scrollHeight > p.clientHeight + 8) {
            const top = el.getBoundingClientRect().top - p.getBoundingClientRect().top + p.scrollTop - 80;
            p.scrollTo(0, Math.max(0, top));
            break;
          }
        }
        """,
        selector,
    )
    time.sleep(0.6)


def capture(base: str, width: int, height: int) -> list[Path]:
    driver = _driver(width, height)
    paths: list[Path] = []
    try:
        driver.get(f"{base}/?embed=true&page=solve&case=0")
        _prepare(driver, "一条干净的推理链")
        paths.append(_shot(driver, "01_case1_hero.png"))
        _scroll_to(driver, ".step")
        paths.append(_shot(driver, "02_case1_steps.png"))

        driver.get(f"{base}/?embed=true&page=solve&case=1")
        _prepare(driver, "12*5=70")
        paths.append(_shot(driver, "03_case2_cards.png"))
        _scroll_to(driver, ".step.root")
        paths.append(_shot(driver, "04_case2_root.png"))

        driver.get(f"{base}/?embed=true&page=solve&case=2")
        _prepare(driver, "Unsupported")
        paths.append(_shot(driver, "05_case3_banner.png"))
        _scroll_to(driver, ".step.root")
        paths.append(_shot(driver, "06_case3_root.png"))

        driver.get(f"{base}/?embed=true&page=dashboard")
        _prepare(driver, "M2 First-Error Exact")
        time.sleep(1.4)
        paths.append(_shot(driver, "07_dashboard_metrics.png"))
        _scroll_to(driver, "[data-testid='stArrowVegaLiteChart'], .stVegaLiteChart, canvas")
        paths.append(_shot(driver, "08_dashboard_chart.png"))
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
            canvas = Image.new("RGB", size, (250, 250, 252))
            canvas.paste(im, (0, 0))
            im = canvas
    return im


def compose_gif(frame_paths: list[Path], width: int, height: int) -> Path:
    durations_ms = [2400, 2200, 1800, 2800, 2600, 2200, 2400, 2200]
    images = [_normalize(p, (width, height)) for p in frame_paths]
    palette_src = images[0].quantize(colors=64, method=Image.Quantize.MEDIANCUT)
    paletted = [im.quantize(palette=palette_src) for im in images]
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    paletted[0].save(
        GIF_PATH,
        save_all=True,
        append_images=paletted[1:],
        duration=durations_ms[: len(paletted)],
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
