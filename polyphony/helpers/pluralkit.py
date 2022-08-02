"""
Functions that pull data from the PluralKit API.
"""
import logging
from typing import Union, List
from urllib import request, error
import json

log = logging.getLogger(__name__)


async def pk_get_system(system_id: str) -> Union[dict, None]:
    """
    Gets a PluralKit system

    :param system_id: PluralKit System ID
    :return: (dict) https://app.swaggerhub.com/apis-docs/xSke/PluralKit/1.0#/Systems/GetSystem
    """
    log.debug(f"Getting system {system_id}")
    try:
        with request.urlopen(f"https://api.pluralkit.me/v2/system/{system_id}") as url:
            return json.loads(url.read().decode())
    except error.URLError as e:
        log.debug(f"Failed to get system {system_id} ({e})")
        return None


async def pk_get_system_members(system_id: str) -> Union[List[dict], None]:
    """
    Gets all members of a PluralKit system

    :param system_id: PluralKit System ID
    :return: (dict) https://app.swaggerhub.com/apis-docs/xSke/PluralKit/1.0#/Members/GetSystemMembers
    """
    log.debug(f"Getting system members of {system_id}")
    try:
        with request.urlopen(
            f"https://api.pluralkit.me/v2/system/{system_id}/members"
        ) as url:
            return json.loads(url.read().decode())
    except error.URLError as e:
        log.debug(f"Failed to get members of system {system_id} ({e})")
        return None


async def pk_get_member(member_id: str) -> Union[dict, None]:
    """
    Get PluralKit member by ID

    :param member_id: PluralKit Member ID
    :return: (dict) https://app.swaggerhub.com/apis-docs/xSke/PluralKit/1.0#/Members/GetMember
    """
    log.debug(f"Getting member {member_id}")
    try:
        with request.urlopen(f"https://api.pluralkit.me/v2/members/{member_id}") as url:
            return json.loads(url.read().decode())
    except error.URLError as e:
        log.debug(f"Failed to get members of system {member_id} ({e})")
        return None
