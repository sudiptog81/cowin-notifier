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

You can also filter vaccination centres by age as shown below:

```txt
You: !vaccine 10d Pune 18
Bot: Vaccines Available in PUNE on 14-05-2021
...
PHC Dorlewadi, Pune (PIN: 413102)
Minimum Age: 18
Shots Available: 4
Vaccine Type: COVAXIN
Fees: Free (₹0)
...
```

## Help

```txt
!vaccine help - Display this help message
!vaccine setup <pincode> - Register PIN code for Notifications
!vaccine setup <pincode> <age> - Register PIN code and Age for Notifications
!vaccine <pincode> <age?> - Check available slots in PIN code, optionally for an age
!vaccine <district-name> <age?> - Check available slots in a District, optionally for an age
!vaccine <n>d <pincode> <age?> - Check available slots 'n' days into future, optionally for an age
!vaccine otp <mobile> - Generate a CoWin OTP
!vaccine verify <mobile> <otp> - Verify the OTP and authenticate the bot
!vaccine me <mobile> - Get details of beneficiaries linked with the mobile number
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
