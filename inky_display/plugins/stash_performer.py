from inky_display.plugins import Base
import logging

import aiohttp
import random
from PIL import Image, UnidentifiedImageError
from io import BytesIO

from stashapi.stashapp import StashInterface
import stashapi.log as log

BASE_TAGS = [
    "-type:gif",
    "-type:swf",
    "-type:webm",
]


class stash_performer(Base):
    def __init__(self, name, config, headers):
        self.logger=logging.getLogger(__name__)
        self.name = name
        self.config = config
        self.stash_conf = {
            "scheme": config["scheme"],
            "host": config["host"],
            "port": config["port"],
            "ApiKey": config["ApiKey"],
            "logger": log,
        }
        self.headders = headers
        self.headders["ApiKey"] = config["ApiKey"]

    async def get_image(self):
        stash = StashInterface(self.stash_conf)
        performers = stash.find_performers()
        while True:
            performer = stash.find_performer(random.choice(performers)["id"])
            img = performer["image_path"]
            async with aiohttp.ClientSession(headers=self.headders) as session:
                self.logger.info(f"downloading {img}")
                async with session.get(img) as r:
                    try:
                        data = Image.open(BytesIO(await r.read()))
                    except UnidentifiedImageError:
                        # Try again
                        self.logger.error(
                            "There was a problem with the image, getting a diffrent one"
                        )
                        continue
                    self.logger.info("Finished Downloading")
                    return data
