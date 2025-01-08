from inky_display.plugins import Base
from inky_display.const import headers
import aiohttp
import random
from PIL import Image
from io import BytesIO

BASE_TAGS = [
    "-type:gif",
    "-type:swf",
    "-type:webm",
]


class e621(Base):
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.domain = "e926.net" if config.get("sfw", False) else "e621.net"

    async def get_image(self):
        tags = self.config.get("tags", [])  # type: list
        tags.extend(BASE_TAGS)
        mode = self.config.get("mode", "random")
        params = {"tags": " ".join(tags)}
        post_url = None
        async with aiohttp.ClientSession(headers=headers) as session:
            while not post_url:
                async with session.get(
                    f"https://{self.domain}/posts.json", params=params
                ) as response:
                    dicts = await response.json()
                    if mode == "random":
                        post = random.choice(dicts["posts"])
                    elif mode == "latest":
                        post = dicts["posts"][0]
                    post_url = post["file"]["url"]
            print(f"getting {post_url}")
            async with session.get(post_url) as r:
                return Image.open(BytesIO(await r.read()))
