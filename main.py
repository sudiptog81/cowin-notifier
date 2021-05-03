import os
import re
import asyncio
import discord
import textwrap
import requests

import auth
import database
from model import *

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

load_dotenv()
client = discord.Client()


async def help_message(message: discord.Message) -> None:
    embed = discord.Embed(
        title=f'CoWin Notifier'
    )
    embed.add_field(name='Help', value=textwrap.dedent('''
    ```txt
    !vaccine help - Display this help message
    !vaccine setup <pincode> - Register Pincode for Notification
    !vaccine <pincode> - Check available slots in Pincode
    !vaccine<n> <pincode> - Check available slots in Pincode, n days into the future
    ```
    '''))
    embed.set_footer(text='Author: @radNerd#1693 | GitHub: @sudiptog81')
    await message.channel.send(embed=embed)


async def setup(message: discord.Message, pincode: str) -> None:
    if (len(pincode) == 0):
        await message.channel.send('No Pincode Specified')
        return

    Session = sessionmaker(bind=database.engine)
    session = Session()
    user = session.query(User).filter_by(
        discord_tag=message.author.id
    ).first()
    if (not user):
        user = User(
            discord_tag=message.author.id,
            pincode=pincode
        )
        session.add(user)
    else:
        user.pincode = pincode
    session.commit()
    session.close_all()
    await message.reply(f'Setup Complete for {pincode}')
    await mention_users()


async def mention_users() -> None:
    Session = sessionmaker(bind=database.engine)
    session = Session()
    users = session.query(User)
    date = datetime.today().strftime(r'%d-%m-%Y')
    for user in users:
        channel = await client.fetch_user(int(user.discord_tag))
        channel = await channel.create_dm()
        if (len(user.pincode) != 6):
            await channel.send('Invalid Pincode ' + user.pincode)
            continue
        embed = discord.Embed(
            title=f'Vaccines Available in {user.pincode} on {date}'
        )
        res = requests.get(
            f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={user.pincode}&date={date}',
            auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
        )
        sessions = res.json()['sessions']
        if (len(sessions) == 0):
            await channel.send(f'<@{user.discord_tag}> No Vaccination Available at {user.pincode} on {date}')
            return
        for center in sessions:
            embed.add_field(
                name=center['name'] + ', ' + center['district_name'],
                value=textwrap.dedent(f'''
            Minimum Age: {center['min_age_limit']}+
            Shots Available: {center['available_capacity']}
            Vaccine Type: {center['vaccine']}
            Fees: {'Free' if center['fee_type'] == 'Free' else 'Paid (₹' + center['fee'] + ')'}
            '''),
                inline=False
            )
        embed.set_footer(text='Source: CoWin API')
        await channel.send(f'<@{user.discord_tag}>')
        await channel.send(embed=embed)
    session.close_all()


async def send_vaccination_slots(message: discord.Message, pincodes: list, date: str) -> None:
    if (len(pincodes) == 0):
        await message.channel.send('No Pincode Specified')
        return
    for pincode in pincodes:
        if (len(pincode) != 6):
            await message.channel.send('Invalid Pincode ' + pincode)
            continue
        embed = discord.Embed(
            title=f'Vaccines Available in {pincode} on {date}'
        )
        res = requests.get(
            f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={pincode}&date={date}',
            auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
        )
        sessions = res.json()['sessions']
        if (len(sessions) == 0):
            await message.channel.send(f'No Vaccination Available at {pincode} on {date}')
            return
        for center in sessions:
            embed.add_field(
                name=center['name'] + ', ' + center['district_name'],
                value=textwrap.dedent(f'''
                Minimum Age: {center['min_age_limit']}+
                Shots Available: {center['available_capacity']}
                Vaccine Type: {center['vaccine']}
                Fees: {'Free' if center['fee_type'] == 'Free' else 'Paid (₹' + center['fee'] + ')'}
                '''),
                inline=False
            )
        embed.set_footer(text='Source: CoWin API')
        await message.channel.send(embed=embed)


@client.event
async def on_ready() -> None:
    print(f'Logged in as {client.user}')
    while True:
        await mention_users()
        await asyncio.sleep(60 * 60 * 20)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return

    if message.content.startswith('!vaccine setup'):
        pincode = message.content.split(' ')[2]
        await setup(message, pincode)

    elif message.content.startswith('!vaccine help'):
        await help_message(message)

    elif message.content.startswith('!vaccine'):
        pincodes = message.content.split(' ')[1:]
        if message.content.split(' ')[0][-1] != 'e':
            date = (
                datetime.today()
                + timedelta(days=int(re.findall('[0-9]+', message.content.split(' ')[0])[0]))
            ).strftime(r'%d-%m-%Y')
        else:
            date = datetime.today().strftime(r'%d-%m-%Y')
        await send_vaccination_slots(message, pincodes, date)

if __name__ == '__main__':
    client.run(os.environ.get('DISCORD_TOKEN'))
