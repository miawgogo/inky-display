from inky_display.plugins import Base
from inky_display.const import headers
import aiohttp
import random
from PIL import Image
from io import BytesIO


class url(Base):
    def __init__(self, name, config):
        self.name = name
        self.config = config

    async def get_image(self):
        url = self.config.get("url", "")  # type: list
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url) as r:
                return Image.open(BytesIO(await r.read()))
