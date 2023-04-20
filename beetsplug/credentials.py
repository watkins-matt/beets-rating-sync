import os
import sys

import confuse
import musicbrainzngs
from confuse import ConfigValueError, NotFoundError

user_agent = "Beets-Rating-Sync"
version = "0.1b"
contact = "https://github.com/watkins-matt/beets-rating-sync"


def load_musicbrainz_credentials():
    beet_config_path = os.path.join(os.environ["BEETSDIR"], "config.yaml")
    if not os.path.exists(beet_config_path):
        os.system.exit(f"Beets config file not found at ${beet_config_path}")

    config = confuse.load_yaml(beet_config_path)

    try:
        mb_user = config["rating_sync"]["mb_user"]
        mb_pass = config["rating_sync"]["mb_pass"]
    except (ConfigValueError, NotFoundError):
        print("Unable to get MusicBrainz credentials from config file.")
        sys.exit(1)

    return mb_user, mb_pass


def init_musicbrainzngs():
    user, password = load_musicbrainz_credentials()
    musicbrainzngs.auth(user, password)
    musicbrainzngs.set_useragent(user_agent, version, contact)
    musicbrainzngs.set_rate_limit(limit_or_interval=1.0, new_requests=1)
