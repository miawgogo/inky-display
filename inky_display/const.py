headers = {
    "User-Agent": "Inky Display",
    "From": "me@miawgogo.dev",  # This is another valid field
}


plain_conf = """
[renderer]
default = "rss.1"
screensaver = "rss.2"
refresh_interval = 5


[plugins]
[plugins.wikimedia.1]
refresh_interval=60
"""