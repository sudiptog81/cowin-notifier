import os
import re
import pickle
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
districts = dict()
client = discord.Client()


async def help_message(message: discord.Message) -> None:
    embed = discord.Embed(
        title=f'CoWin Notifier'
    )
    embed.add_field(name='Usage', value=textwrap.dedent('''
    Query availability for a PIN Code. An example dialogue is given below:

    ```txt
    You: !vaccine 1100001
    Bot: Vaccines Available in 110001 on 04-05-2021
        ...
        MCW Reading Road NDMC PHC, New Delhi
        Minimum Age: 45+
        Shots Available: 49
        Vaccine Type: COVISHIELD
        Fees: Free
        ...
    ```

    You can also check `n` days into the future by using the `!vaccine <n>d <pincode>` format.

    ```txt
    You: !vaccine 10d 1100001
    Bot: Vaccines Available in 110001 on 14-05-2021
        ...
        MCW Reading Road NDMC PHC, New Delhi
        Minimum Age: 45+
        Shots Available: 100
        Vaccine Type: COVAXIN
        Fees: Free
        ...
    ```

    Register a PIN code and use shortcuts. An example dialogue is given below:

    ```txt
    You: !vaccine setup <pincode>
    Bot: Setup Complete for <pincode>
    *ping - check DM*

    You: !vaccine
    Bot: Vaccine Availability in <pincode> on <date> ...

    You: !vaccine 10d
    Bot: Vaccine Availability in <pincode> on <date + 10d> ...
    ```
    '''), inline=False)
    embed.add_field(name='Help', value=textwrap.dedent('''
    ```txt
    !vaccine help - Display this help message
    !vaccine setup <pincode> - Register PIN code for Notifications
    !vaccine <pincode> - Check available slots in PIN code
    !vaccine <district-name> - Check available slots in a District
    !vaccine <n>d <pincode> - Check available slots 'n' days into future
    ```
    '''), inline=False)
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

    date = datetime.today().strftime(r'%d-%m-%Y')
    channel = await message.author.create_dm()
    if (len(pincode) != 6):
        await channel.send('Invalid Pincode ' + pincode)
        return
    await send_dm(channel, message.author.id, pincode, date)


async def mention_users() -> None:
    Session = sessionmaker(bind=database.engine)
    session = Session()
    users = session.query(User)
    date = datetime.today().strftime(r'%d-%m-%Y')
    for user in users:
        _user = await client.fetch_user(int(user.discord_tag))
        channel = await _user.create_dm()

        if (len(user.pincode) != 6):
            await channel.send('Invalid Pincode ' + user.pincode)
            continue

        await send_dm(channel, user.discord_tag, user.pincode, date)
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
            await message.channel.send(f'No Vaccination Available in {pincode} on {date}')
            return
        for center in sessions:
            embed.add_field(
                name=center['name'] + ', ' + center['district_name'],
                value=textwrap.dedent(f'''
                Minimum Age: {center['min_age_limit']}
                Shots Available: {center['available_capacity']}
                Vaccine Type: {center['vaccine']}
                Fees: {'Free' if center['fee_type'] == 'Free' else 'Paid (₹' + center['fee'] + ')'}
                '''),
                inline=False
            )
        embed.set_footer(text='Source: CoWin API')
        await message.channel.send(embed=embed)


async def send_vaccination_slots_by_district(message: discord.Message, district: str, date: str) -> None:
    embed = discord.Embed(
        title=f'Vaccines Available in {district.upper()} on {date}'
    )
    res = requests.get(
        f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id={districts[district]}&date={date}',
        auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
    )
    sessions = res.json()['sessions']
    if (len(sessions) == 0):
        await message.channel.send(f'No Vaccination Available in {district.upper()} on {date}')
        return
    for center in sessions[:25]:
        embed.add_field(
            name=f'''{center['name']}, {center['district_name']} (PIN: {center['pincode']})''',
            value=textwrap.dedent(f'''
            Minimum Age: {center['min_age_limit']}
            Shots Available: {center['available_capacity']}
            Vaccine Type: {center.get('vaccine', '')}
            Fees: {center['fee_type']} (₹{center['fee']})
            '''),
            inline=False
        )
    embed.set_footer(text='Source: CoWin API | Showing the First 25 Results')
    await message.channel.send(embed=embed)


async def send_dm(channel: discord.TextChannel, discord_tag: str, pincode: str, date: str) -> None:
    embed = discord.Embed(
        title=f'Vaccines Available in {pincode} on {date}'
    )
    res = requests.get(
        f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={pincode}&date={date}',
        auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
    )
    sessions = res.json()['sessions']
    if (len(sessions) == 0):
        await channel.send(f'<@{discord_tag}> No Vaccination Available in {pincode} on {date}')
        return
    for center in sessions:
        embed.add_field(
            name=center['name'] + ', ' + center['district_name'],
            value=textwrap.dedent(f'''
        Minimum Age: {center['min_age_limit']}
        Shots Available: {center['available_capacity']}
        Vaccine Type: {center.get('vaccine', '')}
        Fees: {center['fee_type']} (₹{center['fee']})
        '''),
            inline=False
        )
    embed.set_footer(text='Source: CoWin API')
    await channel.send(f'<@{discord_tag}>')
    await channel.send(embed=embed)


def search_district_by_keyword(keywords: list) -> str:
    for district in districts:
        if (keywords in district):
            return district
    return ''


@client.event
async def on_ready() -> None:
    print(f'Logged in as {client.user}')
    while True:
        await asyncio.sleep(60 * 60 * 20)
        await mention_users()


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return

    if message.content.startswith('!vaccine setup'):
        pincode = message.content.split(' ')[2]
        await setup(message, pincode)

    elif message.content.startswith('!vaccine help'):
        await help_message(message)

    elif message.content.split(' ', 1)[0] == '!vaccine':
        days = 0
        pincode = ''

        Session = sessionmaker(bind=database.engine)
        session = Session()
        user = session.query(User).filter_by(
            discord_tag=message.author.id
        ).first()
        if (user):
            pincode = user.pincode
        session.close_all()

        args = message.content.split(' ', 1)[1] \
            if (len(message.content.split(' ', 1)) == 2) else ''

        if (len(re.findall('^\d{1,3}d', args)) != 0):
            days = re.findall('^\d{1,3}d', args)[0].rstrip()[:-1]

        date = (
            datetime.today()
            + timedelta(days=int(days))
        ).strftime(r'%d-%m-%Y')

        pincodes = re.findall('\d{6}', args)
        districts = ' '.join(re.findall('[A-Z|a-z]+', args)).rstrip()[2:]
        print(districts)

        if (len(pincodes) == 0 and pincode != '' and districts == ''):
            await send_vaccination_slots(message, [pincode], date)
            return

        if (len(pincodes) == 0 and (pincode == '' or districts == '')):
            await message.channel.send('No Pincode/District Specified')
            return

        if (len(pincodes) != 0):
            await send_vaccination_slots(message, pincodes, date)
            return

        if (len(districts) != 0):
            district = search_district_by_keyword(districts.lower())
            if (district == ''):
                await message.channel.send('No Such District Found')
                return
            await send_vaccination_slots_by_district(message, district, date)
            return


if __name__ == '__main__':
    with open('districts.pkl', 'rb') as file:
        districts = pickle.load(file)
    client.run(os.environ.get('DISCORD_TOKEN'))
