import json
import os
import asyncio

os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

from livekit.api import AccessToken, CreateAgentDispatchRequest, LiveKitAPI, VideoGrants

from app.config import get_settings


def build_room_name(interview_id: int) -> str:
    return f"interview-{interview_id}"


def create_livekit_token(
    identity: str,
    room_name: str,
    *,
    name: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.livekit_api_key or not settings.livekit_api_secret:
        raise RuntimeError("LiveKit credentials are not configured")

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
    )
    if name:
        token = token.with_name(name)
    return token.to_jwt()


async def _dispatch_agent_async(room_name: str, metadata: dict[str, str | int]) -> str:
    settings = get_settings()
    if not settings.livekit_url or not settings.livekit_api_key or not settings.livekit_api_secret:
        raise RuntimeError("LiveKit credentials are not configured")

    livekit_api = LiveKitAPI(
        settings.livekit_url,
        settings.livekit_api_key,
        settings.livekit_api_secret,
    )
    try:
        dispatch = await livekit_api.agent_dispatch.create_dispatch(
            CreateAgentDispatchRequest(
                agent_name=settings.livekit_agent_name,
                room=room_name,
                metadata=json.dumps(metadata),
            )
        )
        return dispatch.id
    finally:
        await livekit_api.aclose()


def dispatch_agent(room_name: str, metadata: dict[str, str | int]) -> str:
    return asyncio.run(_dispatch_agent_async(room_name, metadata))
