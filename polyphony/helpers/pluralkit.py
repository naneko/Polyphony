"""
Functions that pull data from the PluralKit API.
"""
import logging
import urllib.request
import json

log = logging.getLogger(__name__)

""" Pulls system information from PluralKit API and returns it as dict """


async def pk_get_system(system):
    log.debug("Collecting system data from PluralKit API...")
    try:
        with urllib.request.urlopen("https://api.pluralkit.me/v1/s/" + system) as url:
            system_data = json.loads(url.read().decode())
        return system_data
    except urllib.error.URLError as e: response_data = e.reason
    except urllib.error.HTTPError as e: response_data = e.reason
    log.warning("Urllib Error: Unable to collect system data from PluralKit API")
    return None

""" Pulls Member information from PluralKit API and returns it as dict """


async def pk_get_member(system):
    log.debug("Collecting member data from PluralKit API...")
    try:
        with urllib.request.urlopen("https://api.pluralkit.me/v1/s/" + system + "/members") as url:
            members_data = json.loads(url.read().decode())
            member_list = []

        for item in members_data:
            try:
                member_details = {"id": item['id'],
                                  "name": item['name'],
                                  "color": item['color'],
                                  "display_name": item['display_name'],
                                  "birthday": item['birthday'],
                                  "pronouns": item['pronouns'],
                                  "avatar_url": item['avatar_url'],
                                  "description": item['description'],
                                  "privacy": item['privacy'],
                                  "proxy_tags": item['proxy_tags'],
                                  "keep_proxy": item['keep_proxy'],
                                  "created": item['created'],
                                  "prefix": item['prefix'],
                                  "suffix": item['suffix']}
                member_list.append(member_details)
            except KeyError:
                return None  # or "continue" if this is inside a loop

        return member_list

    except urllib.error.URLError as e: response_data = e.reason
    except urllib.error.HTTPError as e: response_data = e.reason
    log.warning("Urllib Error: Unable to collect member data from PluralKit API")
    return None
