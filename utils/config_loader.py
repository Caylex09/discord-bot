import yaml
from dotenv import load_dotenv
import os


def load_config():
    # 先加载 .env
    load_dotenv()

    # 读功能配置
    with open("config.yml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if config is None:
        config = {}
    if "token" not in config:
        config["token"] = os.getenv("TOKEN")
    if "proxy" not in config:
        config["proxy"] = os.getenv("PROXY")
    return config
