from collections import deque
import asyncio
from PIL import Image, ImageFilter
import logging
import concurrent.futures
from inky.auto import auto
import pathlib
import tomllib
import math
import time
from . import plugins
from .const import HEADERS, DEFAULT_CONF
import traceback


import importlib.resources

MODULE_PATH = importlib.resources.files(__package__)

PAL_ARR = (
    [0x0C, 0x0C, 0x0E]
    + [0xD2, 0xD2, 0xD0]
    + [0x1E, 0x60, 0x1F]
    + [0x1D, 0x1E, 0xAA]
    + [0x8C, 0x1B, 0x1D]
    + [0xD3, 0xC9, 0x3D]
    + [0xC1, 0x71, 0x2A]
)
palIm = Image.new("L", (600, 448))
palIm.putpalette(PAL_ARR)


def make_blur(image: Image):
    change = (image.width - 600) / image.width
    print(change)
    res = (600, math.floor(image.height * abs(change)))
    print(res)
    blur = image.resize(res).filter(ImageFilter.GaussianBlur(radius=2))  # type: Image
    print(res)
    left = 0
    upper = (blur.height - 448) // 2

    return blur.crop((left, upper, left + 600, upper + 448))


def expand2square(pil_img: Image, bg):
    width, height = (600, 448)
    result = bg
    if (pil_img.width, pil_img.height) == (600, 448):
        return pil_img
    elif pil_img.width == width:
        result.paste(pil_img, (0, (height - pil_img.height) // 2))
        return result
    elif pil_img.height == height:
        result.paste(pil_img, ((width - pil_img.width) // 2, 0))
        return result
    else:
        result.paste(
            pil_img, ((width - pil_img.width) // 2, (height - pil_img.height) // 2)
        )
        return result


class Inky_Render:
    def __init__(self, config, pages, logger) -> None:
        self.logger=logger
        self.config = config
        self.pages = pages
        self.page_q = deque(pages.keys())
        self.current_page_name = self.get_default_page()
        self.sync_q()
        self.loop = None
        self.display = auto()
        self.image = Image.new("RGBA", (600, 448), "black")
        self.refresh_break_start = self.get_refresh()

    def run_inky_render(self, image: Image):
        print("Resizing")
        if (image.width, image.height) != self.display.resolution:
            bg = Image.new("RGBA", (600, 448), "black")
            image.thumbnail(self.display.resolution)
            image = expand2square(image, bg)
        print("render start")
        self.display.set_image(image, saturation=0.5)
        self.display.show(busy_wait=False)

    async def render(self):
        self.refresh_break_start = time.time()
        try:
            await self.get_page()
        except Exception as e:
            print(f"Failed to get a new image\r\n{traceback.format_exception(*e)}")

        with concurrent.futures.ThreadPoolExecutor() as pool:
            await self.loop.run_in_executor(pool, self.run_inky_render, self.image)
        print("rendering call finished")

    def get_default_page(self):
        return self.config["renderer"]["default"].split(".")[-1]

    def sync_q(self):
        print(f"syning to {self.current_page_name}")
        while self.page_q[0] != self.current_page_name:
            self.page_q.rotate(1)

    async def get_page(self):
        print(f"getting image from {self.current_page_name}")
        img = await self.pages.get(self.current_page_name).get_image()
        if img is not None:
            self.image = img
        else:
            print("image was none")

    def get_refresh(self):
        """
        gets the refresh interval from the config(specified in minutes) and returns it in seconds
        """
        refresh = self.pages.get(self.current_page_name).get_refresh()
        if not refresh:
            refresh = self.config["renderer"]["refresh_interval"]
        return refresh * 60

    async def main(self):
        self.loop = asyncio.get_running_loop()
        print("starting loop")
        while True:
            timedelta = time.time() - self.refresh_break_start
            if timedelta >= self.get_refresh():
                await self.render()
            await asyncio.sleep(0)


def render_main():
    logger=logging.Logger()
    plug = plugins.Base()
    print(plug.plugins)
    # Load the configuration from the server to get all the possible pages
    conf_dir = pathlib.Path("~/.config/inky/").expanduser()
    if not conf_dir.exists():
        conf_dir.mkdir()
    conf_path = conf_dir.joinpath("inky.toml")
    
    # if the configuration does not exist, write the default one out
    if not conf_path.exists():
        with open(conf_path, "w") as f:
            f.write(DEFAULT_CONF)
            logger.info(f"Configuration Generated, please edit {conf_path}")
    with open(conf_path, "rb") as fp:
        config = tomllib.load(fp)
    pages = {}
    base_headers = HEADERS.copy()
    base_headers["From"] = config["renderer"]["from_email"]
    for pname, p_confs in config["plugins"].items():
        plugin = plug.plugins.get(pname, None)
        if plugin:
            for page_name, page_conf in p_confs.items():
                loadedp = plugin(page_name, page_conf, base_headers.copy())
                pages[page_name] = loadedp
        else:
            logger.error(f"invalid plugin {pname}")
    render = Inky_Render(config, pages, logger)
    asyncio.run(render.main())
