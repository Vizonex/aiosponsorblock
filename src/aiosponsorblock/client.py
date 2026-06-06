import secrets
from collections.abc import MutableMapping, Sequence
from datetime import timedelta
from hashlib import sha256
from types import TracebackType
from typing import Self, TypeVar

from aiohttp import ClientSession
from yarl import URL

from .models import (
    Category,
    SearchedUser,
    Segment,
    SegmentInfo,
    TopUser,
    TotalStats,
    User,
)
from .utils import SortType
from .version import __version__

_K = TypeVar("_K")
_V = TypeVar("_V")


def add_item(
    d: MutableMapping[_K, _V | Sequence[_V]],
    key: _K,
    multi_key: _K,
    items: _K | Sequence[_K],
):
    if not isinstance(items, Sequence):
        d[key] = items
    else:
        d[multi_key] = items


class Client:
    """
    Sponsorblock client for interacting with different servers.
    """

    __slots__ = ("_host", "_stack", "_user_id", "_client")

    def __init__(
        self,
        host: str | URL = "https://sponsor.ajay.app",
        user_id: str | None = None,
        *args,
        **kwargs,
    ):
        self._host = URL(host)
        self._stack.enter_context(self._client)
        self._user_id = user_id or secrets.token_hex(32)
        self._client: ClientSession = ClientSession(*args, **kwargs)

    async def close(self):
        await self._client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def user_id(self):
        return self._user_id

    @property
    def host(self) -> URL:
        return self._host

    async def skip_segments(
        self,
        video_id: str,
        categories: Sequence[Category] | Category,
        required_segments: Sequence[str] | str,
        action_types: Sequence[str] | str,
        service: str | None = None,
    ):
        payload = {"videoID": video_id}
        add_item(payload, "category", "categories", categories)
        add_item(payload, "requiredSegment", "requiredSegments", required_segments)
        add_item(payload, "actionType", "actionTypes", action_types)
        if service:
            payload["service"] = service

        async with self._client.get(
            self._host
            / f"api/skipSegments/{sha256(video_id.encode('utf-8')).hexdigest()[:32]}",
            params=payload,
        ) as resp:
            data = await resp.json()
            for video in data:
                if video["videoID"] == video_id:
                    data = video["segments"]
                    break
        return [Segment.from_dict(d) for d in data]

    async def add_skip_segments(
        self,
        video_id: str,
        segments: list[Segment] | Segment,
        service: str | None = None,
    ) -> bool:
        segments = [segments] if not isinstance(segments, list) else segments
        body = {
            "videoID": video_id,
            "userID": self.user_id,
            "userAgent": f"{__name__}/{__version__}",
            "service": service,
            "segments": [
                {
                    "segment": [
                        s.total_seconds() if isinstance(s, timedelta) else s
                        for s in [segment.start, segment.end]
                    ],
                    "category": segment.category,
                }
                for segment in segments
            ],
        }
        async with self._client.post(
            url=self._host / "api/skipSegments", data=body
        ) as resp:
            return resp.ok

    async def vote_skip_segement(
        self,
        uuid: Segment | str,
        *,
        vote: str | int | bool = None,
        category: Category = None,
    ) -> bool:
        if category is None and vote is None:
            raise ValueError("At least one argument is required")

        if vote in ("yes", "upvote", "up", "good", 1, "1", True, "True"):
            vote = 1
        elif vote in ("no", "downvote", "down", "bad", 0, "0", False, "False"):
            vote = 0
        elif vote in ("undo", 20):
            vote = 20
        else:
            vote = int(bool(vote))

        parameters = {
            "UUID": uuid.uuid if isinstance(uuid, Segment) else uuid,
            "userID": self.user_id,
        }

        if vote is not None:
            parameters["type"] = vote
        if category is not None:
            parameters["category"] = category

        async with self._client.post(
            self._host / "api/voteOnSponsorTime", data=parameters
        ) as resp:
            return resp.ok

    async def post_viewed_video_sponor_time(self, uuid: Segment | str) -> bool:
        async with self._client.post(
            self._host / "api/viewedVideoSponsorTime",
            data={"UUID": uuid.uuid if isinstance(uuid, Segment) else uuid},
        ) as resp:
            return resp.ok

    async def get_user_info(self, public_user_id: str | None = None) -> User:
        if public_user_id is None:
            params = {"userID": self.user_id}
        else:
            params = {"publicUserID": public_user_id}
        async with self._client.get(self._host / "api/userInfo", params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return User.from_dict(data)

    async def get_views_for_user(self) -> int:
        async with self._client.get(
            self._host / "api/getViewsForUser", params={"userID": self.user_id}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["viewCount"]

    async def get_saved_time_for_user(self) -> float:
        async with self._client.get(
            self._host / "api/getSavedTimeForUser", params={"userID": self.user_id}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["timeSaved"]

    async def set_user_name(self, username: str) -> bool:
        async with self._client.post(
            self._host / "api/setUsername",
            data={
                "userID": self.user_id,
                "username": username,
            },
        ) as resp:
            return resp.ok

    async def get_user_name(self) -> str:
        async with self._client.get(
            self._host / "api/getUsername", params={"userID": self.user_id}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["userName"]

    async def get_top_users(self, sort_type: SortType):
        async with self._client.get(
            self._host / "api/getTopUsers",
            params={
                "sortType": sort_type.value
                if isinstance(sort_type, SortType)
                else sort_type
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return [
                TopUser(user_name, view_count, total_submissions, minutes_saved)
                for user_name, view_count, total_submissions, minutes_saved in zip(
                    data["userNames"],
                    data["viewCounts"],
                    data["totalSubmissions"],
                    data["minutesSaved"],
                )
            ]

    async def get_total_stats(
        self, count_contributing_users: bool = False
    ) -> TotalStats:
        async with self._client.get(
            self._host / "api/getTotalStats",
            params={"countContributingUsers": count_contributing_users},
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return TotalStats.from_dict(data)

    async def get_saved_days_formatted(self) -> float:
        async with self._client.get(self._host / "api/getDaysSavedFormatted") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return float(data["daysSaved"])

    async def get_segment_info(
        self, segments: list[Segment | str] | Segment | str
    ) -> list[SegmentInfo]:
        segments = [segments] if not isinstance(segments, list) else segments
        async with self._client.get(
            self._host / "api/segmentInfo",
            params={
                "UUID": [
                    segment.uuid if isinstance(segment, Segment) else str(segment)
                    for segment in segments
                ]
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return [SegmentInfo.from_dict(info) for info in data]

    async def search_for_user(
        self, username: str, exact: bool = False
    ) -> list[SearchedUser]:
        async with self._client.get(
            self._host / "api/userID", params={"username": username, "exact": exact}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return [SearchedUser.from_dict(d) for d in data]
