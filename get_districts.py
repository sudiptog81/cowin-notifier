import os
import pickle
import requests

from dotenv import load_dotenv

import auth

load_dotenv()

with open('states.pkl', 'rb') as file:
    states = pickle.load(file)

districts = dict()
for state in states:
    res = requests.get(
        f'https://cdn-api.co-vin.in/api/v2/admin/location/districts/{states[state]}',
        auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
    )

    res_districts = res.json()['districts']

    for district in res_districts:
        districts[district['district_name'].lower()] = district['district_id']

with open('districts.pkl', 'wb') as file:
    pickle.dump(districts, file)
