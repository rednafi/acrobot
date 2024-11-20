from src.conf import Env, create_settings
from src.log import configure_logger

configure_logger()
settings = create_settings(env=Env.LOCAL)
