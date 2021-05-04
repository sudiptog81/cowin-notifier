import os
import pickle
import requests

from dotenv import load_dotenv

import auth

load_dotenv()

res = requests.get(
    'https://cdn-api.co-vin.in/api/v2/admin/location/states',
    auth=auth.BearerAuth(os.environ.get('COWIN_TOKEN'))
)

res_states = res.json()['states']

states = dict()
for state in res_states:
    states[state['state_name']] = state['state_id']

with open('states.pkl', 'wb') as file:
    pickle.dump(states, file)
