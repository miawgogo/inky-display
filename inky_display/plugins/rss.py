from inky_display.plugins import Base
import logging

import aiohttp
import feedparser
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import traceback


class rss(Base):
    def __init__(self, name, config, headers):
        self.logger=logging.getLogger(__name__)
        self.headers = headers
        self.name = name
        self.config = config
        self.feed = config["feed"]
        self.last_post = None

    async def get_image(self):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(self.feed
            ) as response:
                if "application/xml" not in response.content_type:
                    self.logger.error("Failed to retun feed")
                    return None
                
                try:
                    feed=feedparser.parse(await response.text())
                    soup = BeautifulSoup(feed.entries[0].description, "html.parser")
                    images=soup.find_all("img")
                    post_url = images[0].get("src")
                except Exception as e:
                    self.logger.error(f"Failed to find image due to {traceback.format_exc(*e)}")
                    return None

            self.logger.info(f"getting {post_url}")
            try:
                async with session.get(post_url) as r:
                    if "image" not in r.content_type:
                        self.logger.error("We did not get an image")
                        return None
                    return Image.open(BytesIO(await r.read()))
            except Exception as e:
                self.logger.error(f"failed to download image due to {traceback.format_exc(*e)}")
