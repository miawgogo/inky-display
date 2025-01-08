from inky_display.plugins import Base

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


class stash_gallery(Base):
    def __init__(self, name, config, headers):
        self.name = name
        self.config = config
        self.domain = "e926.net" if config.get("sfw", False) else "e621.net"
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
        gals = stash.find_galleries()
        while True:
            gal = stash.find_gallery_images(random.choice(gals)["id"])
            img = random.choice(gal)["paths"]["thumbnail"]
            async with aiohttp.ClientSession(headers=self.headders) as session:
                print(f"downloading {img}")
                async with session.get(img) as r:
                    try:
                        data = Image.open(BytesIO(await r.read()))
                    except UnidentifiedImageError:
                        # Try again
                        print(
                            "There was a problem with the image, getting a diffrent one"
                        )
                        continue
                    print("Finished Downloading")
                    return data
