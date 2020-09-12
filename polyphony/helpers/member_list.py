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
        member_user = ctx.guild.get_member(member["member_account_id"])
        owner_user = ctx.guild.get_member(member["discord_account_id"])
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
                name=dict(member).get("display_name", member["member_name"]),
                value=f"""**User:** {member_user.mention}\n**PluralKit Member ID:** `{member['pk_member_id']}`\n**Tags:** {' or '.join(tags)}\n**Enabled:** `{'Yes' if member['member_enabled'] else 'No'}`""",
                inline=True,
            )
        else:
            embed.add_field(
                name=dict(member).get("display_name", member["member_name"]),
                value=f"""**User:** {member_user.mention} (`{member_user.id}`)\n**Account Owner:** {owner_user.mention if hasattr(owner_user, 'mention') else "*Unable to get User*"} (`{member["discord_account_id"]}`)\n**PluralKit Member ID:** `{member['pk_member_id']}`\n**Tag(s):** {' or '.join(tags)}\n**Enabled:** `{'Yes' if member['member_enabled'] else 'No'}`""",
                inline=True,
            )

    await ctx.send(embed=embed)
