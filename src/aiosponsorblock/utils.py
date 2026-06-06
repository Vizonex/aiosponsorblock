import re
from enum import Enum
from typing import Literal

VIDEO_ID_REGEX = re.compile(
    r"(.+?)(\/)(watch\x3Fv=)?(embed\/watch\x3Ffeature\=player_embedded\x26v=)?([a-zA-Z0-9_-]{11})+"
)
ALL_CATEGORIES = [
    "sponsor",
    "selfpromo",
    "interaction",
    "intro",
    "outro",
    "preview",
    "music_offtopic",
    "poi_highlight",
    "filler",
]
Category = Literal[
    "sponsor",
    "selfpromo",
    "interaction",
    "intro",
    "outro",
    "preview",
    "music_offtopic",
    "poi_highlight",
    "filler",
]


class SortType(Enum):
    """0 for by minutes saved, 1 for by view count, 2 for by total submissions

    See Also
    --------
    sponsorblock.client.Client.get_top_users : Should be used with the SortType
    """

    MINUTES_SAVED = 0
    VIEW_COUNT = 1
    TOTAL_SUBMISSIONS = 2
