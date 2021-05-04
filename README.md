# CoWin Notifier

[![discord](https://img.shields.io/static/v1?style=for-the-badge&logo=discord&message=Invite&label=Discord&labelColor=&color=7289da)](https://discord.com/api/oauth2/authorize?client_id=838664980584726538&permissions=18432&scope=bot)

## Usage

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

You can also check `n` days into the future by using the `!vaccine <n>d` prefix.

```txt
You: !vaccine 10d Pune
Bot: Vaccines Available in PUNE on 14-05-2021
     ...
     PHC Dorlewadi, Pune (PIN: 413102)
     Minimum Age: 45
     Shots Available: 44
     Vaccine Type: COVISHIELD
     Fees: Free (₹0)
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

## Help

```txt
!vaccine help - Display this help message
!vaccine setup <pincode> - Register PIN code for Notifications
!vaccine <pincode> - Check available slots in PIN code
!vaccine <district-name> - Check available slots in a District
!vaccine <n>d <pincode> - Check available slots 'n' days into future
```

## Quick Start

Clone the repository and change to the directory.

Populate `.env` with the variables given in `.env.sample`.

Create a virtual environment and install dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

Run the bot.

```bash
python3 main,py
```
