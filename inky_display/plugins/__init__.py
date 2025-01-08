import os
import traceback
from importlib import util


class Base:
    """Basic resource class. Concrete resources will inherit from this one"""

    plugins = {}

    def get_refresh(self):
        return self.config.get("refresh_interval", None)

    # For every class that inherits from the current,
    # the class name will be added to plugins
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.plugins[cls.__name__] = cls


# Small utility to automatically load modules
def load_module(path):
    fname=path.split("/")[-1].split(".")[0]
    name = f"{__name__}.{fname}"
    spec = util.spec_from_file_location(name, path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Get current path
path = os.path.abspath(__file__)
dirpath = os.path.dirname(path)

for fname in os.listdir(dirpath):
    # Load only "real modules"
    if (
        not fname.startswith(".")
        and not fname.startswith("__")
        and fname.endswith(".py")
    ):
        try:
            load_module(os.path.join(dirpath, fname))
        except Exception:
            traceback.print_exc()
