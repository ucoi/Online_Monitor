#!/usr/bin/env python3
"""
Test script to see what the OnlineSim API actually returns
"""

import requests
import json
from config import *

# Test with Ukraine (country code 380)
print("Testing OnlineSim API...")
print(f"API Key: {ONLINESIM_API_KEY[:10]}...")
print()

# Try different API endpoints to find the right one
endpoints = [
    {
        'name': 'getFreePhoneList',
        'url': f"{ONLINESIM_API_URL}/getFreePhoneList.php",
        'params': {'apikey': ONLINESIM_API_KEY, 'country': 380, 'service': SERVICE}
    },
    {
        'name': 'getNumbersStats',
        'url': f"{ONLINESIM_API_URL}/getNumbersStats.php",
        'params': {'apikey': ONLINESIM_API_KEY, 'country': 380, 'service': SERVICE}
    },
    {
        'name': 'getState',
        'url': f"{ONLINESIM_API_URL}/getState.php",
        'params': {'apikey': ONLINESIM_API_KEY, 'type': 'free'}
    },
    {
        'name': 'getNum (Ukraine)',
        'url': f"{ONLINESIM_API_URL}/getNum.php",
        'params': {'apikey': ONLINESIM_API_KEY, 'service': SERVICE, 'country': 380}
    },
]

for endpoint in endpoints:
    print(f"\n{'='*70}")
    print(f"Testing: {endpoint['name']}")
    print(f"URL: {endpoint['url']}")
    print(f"Params: {endpoint['params']}")
    print('-'*70)
    
    try:
        response = requests.get(endpoint['url'], params=endpoint['params'], timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response:")
        
        try:
            data = response.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except:
            print(response.text)
            
    except Exception as e:
        print(f"Error: {e}")

print(f"\n{'='*70}")
print("\nNow testing with Hungary (country code 36):")
print('-'*70)

try:
    url = f"{ONLINESIM_API_URL}/getNumbersStats.php"
    params = {'apikey': ONLINESIM_API_KEY, 'country': 36, 'service': SERVICE}
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    response = requests.get(url, params=params, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(response.text)
        
except Exception as e:
    print(f"Error: {e}")
