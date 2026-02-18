import logging
import yaml
from urllib.request import urlopen

logger = logging.getLogger(__name__)


def fetch_yaml(url: str):
    logger.debug("Fetching JSON/YAML data from %s", url)
    with urlopen(url) as f:
        return yaml.safe_load(f)
