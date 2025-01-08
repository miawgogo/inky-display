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
class Inky_Render:
    def __init__(self, config, pages) -> None:
        self.logger=logging.getLogger(__name__)
        self.config = config
        self.pages = pages
        self.page_q = deque(pages.keys())
        self.current_page_name = self.get_default_page()
        self.sync_q()
        self.loop = None
        self.display = auto()
        self.image = Image.new("RGBA", self.display.resolution, "black")
        self.refresh_break_start = self.get_refresh()

    def run_inky_render(self, image: Image):
        self.logger.info("Resizing")
        if (image.width, image.height) != self.display.resolution:
            bg = Image.new("RGBA", self.display.resolution, "black")
            image.thumbnail(self.display.resolution)
            image = self.expand2square(image, bg)
        self.logger.info("render start")
        self.display.set_image(image, saturation=0.5)
        self.display.show(busy_wait=False)

    def make_blur(self, image: Image):
        change = (image.width - 600) / image.width
        print(change)
        res = (600, math.floor(image.height * abs(change)))
        print(res)
        blur = image.resize(res).filter(ImageFilter.GaussianBlur(radius=2))  # type: Image
        print(res)
        left = 0
        upper = (blur.height - 448) // 2

        return blur.crop((left, upper, left + 600, upper + 448))


    def expand2square(self, pil_img: Image, bg):
        width, height = self.display.resolution
        result = bg
        if (pil_img.width, pil_img.height) == self.display.resolution:
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

    async def render(self):
        self.refresh_break_start = time.time()
        try:
            await self.get_page()
        except Exception as e:
            self.logger.error(
                f"Failed to get a new image\r\n{traceback.format_exception(*e)}"
            )

        with concurrent.futures.ThreadPoolExecutor() as pool:
            await self.loop.run_in_executor(pool, self.run_inky_render, self.image)
        self.logger.info("rendering call finished")

    def get_default_page(self):
        return self.config["renderer"]["default"].split(".")[-1]

    def sync_q(self):
        self.logger.info(f"Syncing to {self.current_page_name}")
        while self.page_q[0] != self.current_page_name:
            self.page_q.rotate(1)

    async def get_page(self):
        self.logger.info(f"getting image from {self.current_page_name}")
        img = await self.pages.get(self.current_page_name).get_image()
        if img is not None:
            self.image = img
        else:
            self.logger.info("image was none")

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
        self.logger.info("starting loop")
        while True:
            timedelta = time.time() - self.refresh_break_start
            if timedelta >= self.get_refresh():
                await self.render()
            await asyncio.sleep(0)


def render_main():
    logger = logging.getLogger(__name__)
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
    render = Inky_Render(config, pages)
    asyncio.run(render.main())
