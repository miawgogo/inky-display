from inky_display.plugins import Base
import logging

import aiohttp
import feedparser
from bs4 import BeautifulSoup
import datetime
from PIL import Image
from io import BytesIO
import traceback

wikimedia_api = "https://commons.wikimedia.org/w/api.php"


class wikimedia(Base):
    def __init__(self, name, config, headers):
        self.logger=logging.getLogger(__name__)
        self.headers = headers
        self.name = name
        self.config = config
        self.iso_day=None

    async def fetch_image_src(self, filename):
        # https://www.mediawiki.org/wiki/API:Picture_of_the_day_viewer based on this example because this is a personal project
        async with aiohttp.ClientSession(headers=self.headers) as session:
            params = {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "iiprop": "url",
                "titles": filename,
            }

            async with session.get(wikimedia_api, params=params) as response:
                data = await response.json()
                page = next(iter(data["query"]["pages"].values()))
                image_info = page["imageinfo"][0]
                image_url = image_info["url"]

                return image_url
    
    async def get_image(self):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            date_iso = datetime.date.today().isoformat()
            if date_iso == self.iso_day:
                self.logger.info("Last update was the same day, skipping")
                return None
            title = "Template:Potd/" + date_iso
            params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "images",
                "titles": title
            }
            async with session.get(wikimedia_api, params=params) as response:
                data = await response.json()
                filename=data["query"]["pages"][0]["images"][0]["title"]
            post_url = await self.fetch_image_src(filename)

            self.logger.info(f"getting {post_url}")
            try:
                async with session.get(post_url) as r:
                    if "image" not in r.content_type:
                        self.logger.error("We did not get an image")
                        return None
                    self.iso_day = date_iso
                    return Image.open(BytesIO(await r.read()))
                    
            except Exception as e:
                self.logger.error(
                    f"failed to download image due to {traceback.format_exc(*e)}"
                )
