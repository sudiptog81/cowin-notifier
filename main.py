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

from hashlib import sha256
from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

load_dotenv()
txns = dict()
tokens = dict()
districts = dict()
client = discord.Client()
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36'
}


async def help_message(message: discord.Message) -> None:
    embed = discord.Embed(
        title=f'CoWin Notifier'
    )
    embed.add_field(name='Setup', value=textwrap.dedent('''
    ```txt
    !vaccine setup <district> <age?>
    ```

    '''), inline=False)
    embed.add_field(name='Help', value=textwrap.dedent('''
    ```txt
    !vaccine help - Display this help message
    !vaccine setup <district> - Register District for Notifications
    !vaccine setup <district> <age> - Register District and Age for Notifications
    !vaccine <pincode> <age?> - Check available slots in PIN code, optionally for an age
    !vaccine <district> <age?> - Check available slots in a District, optionally for an age
    !vaccine <n>d <pincode/district> <age?> - Check available slots 'n' days into future, optionally for an age
    !vaccine otp <mobile> - Generate a CoWin OTP
    !vaccine verify <mobile> <otp> - Verify the OTP and authenticate the bot
    !vaccine me <mobile> - Get details of beneficiaries linked with the mobile number
    !vaccine - Check available slots in the District you have registered for
    !vaccine <n>d - Check available slots in the District you have registered for, 'n' days into future
    !vaccine unsubscribe - Opt out from notifications
    ```
    '''), inline=False)
    embed.set_footer(text='Author: @radNerd#1693 | GitHub: @sudiptog81')
    await message.channel.send(embed=embed)


async def setup(message: discord.Message, district: str, min_age: int) -> None:
    try:
        Session = sessionmaker(bind=database.engine)
        session = Session()
        user = session.query(User).filter_by(
            discord_tag=message.author.id
        ).first()

        if (not user):
            user = User(
                discord_tag=message.author.id,
                district=district,
                min_age=min_age
            )
            session.add(user)
        else:
            user.district = district
            user.min_age = min_age

        session.commit()
        await message.reply(f'Setup Complete for {district.upper()}')
        print(f'=> Registered {message.author.display_name}...')
        date = datetime.today().strftime(r'%d-%m-%Y')
        channel = await message.author.create_dm()
        discord_name = f'@{message.author.name}#{message.author.discriminator}'
        await send_dm(channel, message.author.id, district, date, min_age, discord_name)
    except Exception as e:
        print(f'=> Error: {e}')
        session.rollback()
        await message.reply('Could not complete the setup. Contact @ScientificGhosh on Twitter.')
    finally:
        session.close()


async def unsubscribe(message: discord.Message) -> None:
    try:
        Session = sessionmaker(bind=database.engine)
        session = Session()
        user = session.query(User).filter_by(
            discord_tag=message.author.id
        ).first()

        if (not user):
            await message.reply('You are not subscribed in the first place')
            return

        session.delete(user)
        session.commit()

        await message.reply('You will not receive notifications from now on')
        print(f'=> Deleted {message.author.display_name}...')
    except Exception as e:
        print(f'=> Error: {e}')
        session.rollback()
        await message.reply('Could not complete the deregistration. Contact @ScientificGhosh on Twitter.')
    finally:
        session.close()


async def mention_users() -> None:
    print('=> Polling...')
    Session = sessionmaker(bind=database.engine)
    session = Session()
    users = session.query(User)
    dates = [
        datetime.today().strftime(r'%d-%m-%Y'),
        (datetime.today() + timedelta(days=7)).strftime(r'%d-%m-%Y'),
        (datetime.today() + timedelta(days=14)).strftime(r'%d-%m-%Y')
    ]
    for user in users:
        _user = await client.fetch_user(int(user.discord_tag))
        discord_name = f'@{_user.name}#{_user.discriminator}'
        channel = await _user.create_dm()
        for date in dates:
            await send_dm(channel, user.discord_tag, user.district, date, user.min_age, discord_name)
            await asyncio.sleep(10)
    session.close()


async def send_vaccination_slots(message: discord.Message, pincodes: list, date: str, min_age: int) -> None:
    if (len(pincodes) == 0):
        await message.channel.send('No Pincode Specified')
        return
    try:
        print(
            f'=> Query from @{message.author.display_name}#{message.author.discriminator}'
        )
        for pincode in pincodes:
            if (len(pincode) != 6):
                await message.channel.send('Invalid Pincode ' + pincode)
                continue
            embed = discord.Embed(
                title=f'Vaccines Available in {pincode} on {date}'
            )
            res = requests.get(
                f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByPin?pincode={pincode}&date={date}',
                headers=headers
            )
            sessions = res.json()['sessions']
            if (len(sessions) == 0):
                await message.channel.send(f'No Vaccination Available in {pincode} on {date}.')
                return
            for center in sessions:
                if (int(center.get('min_age_limit')) == min_age):
                    embed.add_field(
                        name=center.get('name') + ', ' +
                        center.get('district_name'),
                        value=textwrap.dedent(f'''
                        Minimum Age: {center.get('min_age_limit')}
                        Shots Available: {center.get('available_capacity')} (Dose 1: {center.get('available_capacity_dose1', '-')}; Dose 2: {center.get('available_capacity_dose2', '-')})
                        Vaccine Type: {center.get('vaccine')}
                        Fees: {center.get('fee_type')} (₹{center.get('fee', '-')})
                        '''),
                        inline=False
                    )
            embed.set_footer(text='Source: CoWin API')
            if (len(embed.fields) != 0):
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f'No Vaccination Available in {pincode} on {date} for given criteria.')
    except Exception as e:
        print(f'=> Error: {e}')
        await message.channel.send('Internal Error. Contact @ScientificGhosh on Twitter.')


async def send_vaccination_slots_by_district(message: discord.Message, district: str, date: str, min_age: int) -> None:
    try:
        print(
            f'=> Query from @{message.author.display_name}#{message.author.discriminator}'
        )
        embed = discord.Embed(
            title=f'Vaccines Available in {district.upper()} on {date}'
        )
        res = requests.get(
            f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/findByDistrict?district_id={districts[district]}&date={date}',
            headers=headers
        )
        sessions = res.json()['sessions']
        if (len(sessions) == 0):
            await message.channel.send(f'No Vaccination Available in {district.upper()} on {date}.')
            return
        for center in sessions[:25]:
            if (int(center.get('min_age_limit')) == min_age):
                embed.add_field(
                    name=f'''{center.get('name')}, {center.get('district_name')} (PIN: {center.get('pincode')})''',
                    value=textwrap.dedent(f'''
                    Minimum Age: {center.get('min_age_limit')}
                    Shots Available: {center.get('available_capacity')} (Dose 1: {center.get('available_capacity_dose1', '-')}; Dose 2: {center.get('available_capacity_dose2', '-')})
                    Vaccine Type: {center.get('vaccine', '')}
                    Fees: {center.get('fee_type')} (₹{center.get('fee', '-')})
                    '''),
                    inline=False
                )
        embed.set_footer(
            text='Source: CoWin API | Showing the First 25 Results')
        if (len(embed.fields) != 0):
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(f'No Vaccination Available in {district.upper()} on {date} for given criteria.')
    except Exception as e:
        print(e)
        await message.channel.send('Internal Error. Contact @ScientificGhosh on Twitter.')


async def send_dm(channel: discord.TextChannel, discord_tag: str, district: str, date: str, min_age: int, discord_name: str) -> None:
    try:
        res = requests.get(
            f'https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={districts[district]}&date={date}',
            headers=headers
        )
        centers = res.json()['centers']
        if (len(centers) == 0):
            return
        embed = discord.Embed(
            title=f'''Vaccines Available in {district.upper()} in Next Few Days'''
        )
        count = 0
        for center in centers:
            for session in center['sessions']:
                if (int(session.get('min_age_limit')) == min_age
                        and session.get('available_capacity') != 0):
                    if count > 24:
                        break
                    embed.add_field(
                        name=f'''{center.get('name')}, PIN {center.get('pincode')} ({session.get('date')})''',
                        value=textwrap.dedent(f'''
                        Minimum Age: {session.get('min_age_limit')}
                        Shots Available: {session.get('available_capacity')} (Dose 1: {session.get('available_capacity_dose1', '-')}; Dose 2: {session.get('available_capacity_dose2', '-')})
                        Vaccine Type: {session.get('vaccine', '')}
                        Fees: {session.get('fee_type')} (₹{session.get('fee', '-')})
                        '''),
                        inline=False
                    )
                    count += 1
        embed.set_footer(text='Source: CoWin API')

        if (len(embed.fields) != 0):
            embed.add_field(
                name='Slot Booking',
                value='[https://selfregistration.cowin.gov.in/](https://selfregistration.cowin.gov.in/)'
            )
            await channel.send(embed=embed)
            print(f'... Message sent to {discord_name}')
    except Exception as e:
        print(e)
        await channel.send('Internal Error. Contact @ScientificGhosh on Twitter.')


def search_district_by_keyword(keywords: list) -> str:
    for district in districts:
        if (keywords in district):
            return district
    return ''


@client.event
async def on_ready() -> None:
    print(f'Logged in as {client.user}')
    await client.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name='!vaccine help'
        )
    )
    while True:
        await mention_users()
        await asyncio.sleep(60 * 5)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author == client.user:
        return

    if message.content.startswith('!vaccine setup'):
        if (len(message.content.split(' ')) <= 2):
            await message.reply('No district mentioned')
            return

        args = ' '.join(message.content.split(' ')[2:])

        keywords = ' '.join(re.findall('[A-Z|a-z|()]+', args))
        district = search_district_by_keyword(keywords.lower())

        if (district == ''):
            await message.channel.send('No Such District Found')
            return

        min_age = re.findall(' \d{2}$', args)
        if (len(min_age) != 0):
            min_age = 18 if int(min_age[0]) < 45 else 45
        else:
            min_age = 18

        await setup(message, district, min_age)

    elif message.content.startswith('!vaccine unsubscribe'):
        await unsubscribe(message)
    elif message.content.startswith('!vaccine otp'):
        args = ' '.join(message.content.split(' '))
        mobiles = re.findall(' \d{10}$', args)
        if (len(mobiles) == 0):
            await message.reply('No Mobile Number mentioned')
            return
        mobile = mobiles[0][1:]
        res = requests.post(
            f'https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP',
            json={
                'mobile': f'{mobile}',
                'secret': os.environ.get('COWIN_SECRET')
            },
            headers=headers
        )
        txns[mobile] = res.json()['txnId']
        await message.reply('OTP sent to your phone')

    elif message.content.startswith('!vaccine verify'):
        args = ' '.join(message.content.split(' '))

        mobiles = re.findall(' \d{10}', args)
        if (len(mobiles) == 0):
            await message.reply('No Mobile Number mentioned')
            return
        mobile = mobiles[0][1:]

        if mobile not in txns:
            await message.reply('Retry to send OTP and then verify')
            return

        otps = re.findall(' \d{6}$', args)
        if (len(otps) == 0):
            await message.reply('No OTP mentioned')
            return
        otp = otps[0][1:]

        res = requests.post(
            f'https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp',
            json={
                'otp': sha256(otp.encode('utf-8')).hexdigest(),
                'txnId': txns[mobile]
            },
            headers=headers
        )

        tokens[mobile] = res.json()['token']

        await message.reply(textwrap.dedent(f'''
            OTP Verified
            ```txt
            {res.json()['token']}
            ```
        '''))

    elif message.content.startswith('!vaccine me'):
        args = ' '.join(message.content.split(' '))

        mobiles = re.findall(' \d{10}', args)
        if (len(mobiles) == 0):
            await message.reply('No Mobile Number mentioned')
            return
        mobile = mobiles[0][1:]

        if mobile not in tokens:
            await message.reply('Reauthenticate by sending OTP and verifying')
            return

        res = requests.get(
            f'https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries',
            auth=auth.BearerAuth(tokens[mobile]),
            headers=headers
        )

        people = res.json()['beneficiaries'][0]
        embed = discord.Embed(
            title=f'''{people.get('name')}'''
        )
        embed.add_field(
            name='Year of Birth',
            value=people.get('birth_year'),
            inline=False
        )
        embed.add_field(
            name='Gender',
            value=people.get('gender'),
            inline=False
        )
        embed.add_field(
            name='ID Proof',
            value=f'''{people.get('photo_id_type')} ({people.get('photo_id_number')})''',
            inline=False
        )
        embed.add_field(
            name='Status',
            value=people.get('vaccination_status'),
            inline=False
        )
        await message.reply(embed=embed)

    elif message.content.startswith('!vaccine help'):
        await help_message(message)

    elif message.content.split(' ', 1)[0] == '!vaccine':
        days = 0
        district = ''
        min_age = 45

        Session = sessionmaker(bind=database.engine)
        session = Session()
        user = session.query(User).filter_by(
            discord_tag=message.author.id
        ).first()
        if (user):
            district = user.district
            min_age = user.min_age
        session.close()

        args = message.content.split(' ', 1)[1] \
            if (len(message.content.split(' ', 1)) == 2) else ''

        if (len(re.findall('^\d{1,3}d', args)) != 0):
            days = re.findall('^\d{1,3}d', args)[0].rstrip()[:-1]

        date = (
            datetime.today()
            + timedelta(days=int(days))
        ).strftime(r'%d-%m-%Y')

        pincodes = re.findall('\d{6}', args)
        keywords = ' '.join(re.findall('[A-Z|a-z|()]+', args)).rstrip()[2:] \
            if (days != 0) else ' '.join(re.findall('[A-Z|a-z]+', args)).rstrip()

        min_age_arg = re.findall(' \d{2}$', args)
        if (len(min_age_arg) != 0):
            min_age = 18 if int(min_age_arg[0]) < 45 else 45

        if (len(pincodes) == 0 and district != '' and keywords == ''):
            await send_vaccination_slots_by_district(message, district, date, min_age)
            return

        if (len(pincodes) == 0 and (discord == '' and keywords == '')):
            await message.channel.send('No Pincode/District Specified')
            return

        if (len(pincodes) != 0):
            await send_vaccination_slots(message, pincodes, date, min_age)
            return

        if (len(keywords) != 0):
            district = search_district_by_keyword(keywords.lower())
            if (district == ''):
                await message.channel.send('No Such District Found')
                return
            await send_vaccination_slots_by_district(message, district, date, min_age)
            return


if __name__ == '__main__':
    with open('districts.pkl', 'rb') as file:
        districts = pickle.load(file)
    client.run(os.environ.get('DISCORD_TOKEN'))
