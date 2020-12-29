import json
import sqlite3
from typing import List

import discord
from discord.ext import commands


async def send_member_list(
    ctx: commands.context, embed, member_list: List[sqlite3.Row], whoarewe=False
):
    if member_list is None:
        embed.add_field(name="No members where found")

    for member in member_list:
        if len(embed.fields) >= 9:
            await ctx.send(embed=embed)
            embed = discord.Embed()
        member_user = ctx.guild.get_member(member["id"])
        owner_user = ctx.guild.get_member(member["main_account_id"])
        tags = []
        for tag in json.loads(member["pk_proxy_tags"]):
            tags.append(
                "`"
                + (tag.get("prefix") or "")
                + "text"
                + (tag.get("suffix") or "")
                + "`"
            )
        if whoarewe:
            embed.add_field(
                name=member["member_name"],
                value=f"""> **User:** {member_user.mention if hasattr(member_user, 'mention') else ":warning: *Unable to get User*"}\n"""
                f"""> **PluralKit Member ID:** `{member['pk_member_id']}`\n"""
                f"""> **Tags:** {' or '.join(tags)}\n"""
                f"""> **Enabled:** {':white_check_mark:' if member['member_enabled'] else ':x:'}""",
                inline=True,
            )
        else:
            embed.add_field(
                name=member["member_name"],
                value=f"""> **User:** {member_user.mention if hasattr(member_user, 'mention') else ":warning: *Unable to get User*"} (`{member["id"]}`)\n"""
                f"""> **Account Owner:** {owner_user.mention if hasattr(owner_user, 'mention') else ":warning: *Unable to get User*"} (`{member["main_account_id"]}`)\n"""
                f"""> **Nickname:** {f"`{member['nickname']}` *(Nick)*" if member['nickname'] and len(member['nickname'] or "") < 32 else (f"`{member['display_name']}` *(Display)*" if member['display_name'] else "`None`")} {"*(:warning: Set nickname too long)*" if len(member['nickname'] or "") > 32 else ""}\n"""
                f"""> **PluralKit Member ID:** `{member['pk_member_id']}`\n"""
                f"""> **Tag(s):** {' or '.join(tags)}\n"""
                f"""> **Enabled:** {':white_check_mark:' if member['member_enabled'] else ':x:'}""",
                inline=False,
            )

    await ctx.send(embed=embed)
