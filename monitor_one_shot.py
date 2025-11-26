#!/usr/bin/env python3
"""
Single-run OnlineSim monitor for CI (GitHub Actions) or cron.
- Reads configuration from environment variables (falling back to `config.py`).
- Persists state to `state.json` so cooldowns survive between runs.
- Optionally purchases numbers if `AUTO_PURCHASE` is enabled via env var.
"""
import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path

# Try to import local config for defaults
try:
    from config import *
except Exception:
    # Provide sane defaults if config not available
    ONLINESIM_API_KEY = os.environ.get('ONLINESIM_API_KEY', '')
    ONLINESIM_API_URL = os.environ.get('ONLINESIM_API_URL', 'https://onlinesim.io/api')
    SERVICE = os.environ.get('SERVICE', 'foodora')
    COUNTRY = int(os.environ.get('COUNTRY', 36))
    EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL', '')
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', '')
    RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', '')
    CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', 300))
    COOLDOWN_AFTER_NOTIFICATION = int(os.environ.get('COOLDOWN_AFTER_NOTIFICATION', 3600))
    RECHECK_INTERVAL_IF_STILL_AVAILABLE = int(os.environ.get('RECHECK_INTERVAL_IF_STILL_AVAILABLE', 1800))
    AUTO_PURCHASE = os.environ.get('AUTO_PURCHASE', 'false').lower() == 'true'
    PURCHASE_QUANTITY = int(os.environ.get('PURCHASE_QUANTITY', 2))

# Allow env overrides for safety
ONLINESIM_API_KEY = os.environ.get('ONLINESIM_API_KEY', ONLINESIM_API_KEY)
ONLINESIM_API_URL = os.environ.get('ONLINESIM_API_URL', ONLINESIM_API_URL)
SERVICE = os.environ.get('SERVICE', SERVICE)
COUNTRY = int(os.environ.get('COUNTRY', COUNTRY))
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', str(EMAIL_ENABLED)).lower() == 'true'
SMTP_SERVER = os.environ.get('SMTP_SERVER', SMTP_SERVER)
SMTP_PORT = int(os.environ.get('SMTP_PORT', SMTP_PORT))
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', SENDER_EMAIL)
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD', SENDER_PASSWORD)
RECIPIENT_EMAIL = os.environ.get('RECIPIENT_EMAIL', RECIPIENT_EMAIL)
COOLDOWN_AFTER_NOTIFICATION = int(os.environ.get('COOLDOWN_AFTER_NOTIFICATION', COOLDOWN_AFTER_NOTIFICATION))
RECHECK_INTERVAL_IF_STILL_AVAILABLE = int(os.environ.get('RECHECK_INTERVAL_IF_STILL_AVAILABLE', RECHECK_INTERVAL_IF_STILL_AVAILABLE))
AUTO_PURCHASE = os.environ.get('AUTO_PURCHASE', str(AUTO_PURCHASE)).lower() == 'true'
PURCHASE_QUANTITY = int(os.environ.get('PURCHASE_QUANTITY', PURCHASE_QUANTITY if 'PURCHASE_QUANTITY' in globals() else 2))

STATE_FILE = Path('state.json')
PURCHASES_FILE = Path('purchased_numbers.json')

# Load or init state
if STATE_FILE.exists():
    try:
        state = json.loads(STATE_FILE.read_text())
    except Exception:
        state = {}
else:
    state = {}

last_notified = None
if 'last_notification_time' in state:
    try:
        last_notified = datetime.fromisoformat(state['last_notification_time'])
    except Exception:
        last_notified = None

numbers_were_available = state.get('numbers_were_available', False)

# Helper: save state
def save_state():
    state['last_notification_time'] = last_notified.isoformat() if last_notified else None
    state['numbers_were_available'] = numbers_were_available
    STATE_FILE.write_text(json.dumps(state, indent=2))

# Helper: log
def info(msg):
    print(f"{datetime.now().isoformat()} INFO {msg}")

# 1) Check numbers stats
info(f"Checking OnlineSim for {SERVICE} in country {COUNTRY}")
try:
    url = f"{ONLINESIM_API_URL}/getNumbersStats.php"
    params = {'apikey': ONLINESIM_API_KEY, 'country': COUNTRY, 'service': SERVICE}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
except Exception as e:
    info(f"API error: {e}")
    exit(1)

# Parse response
count = 0
price = 'N/A'
if isinstance(data, dict) and 'services' in data:
    key = f"service_{SERVICE}"
    if key in data['services']:
        svc = data['services'][key]
        count = int(svc.get('count', 0))
        price = svc.get('price', 'N/A')

if count <= 0:
    info("No numbers available")
    numbers_were_available = False
    # save state (clear last_notification_time if more than cooldown?)
    if last_notified:
        # if last notification older than cooldown, clear
        if (datetime.now() - last_notified).total_seconds() > COOLDOWN_AFTER_NOTIFICATION:
            last_notified = None
    state['last_notification_time'] = last_notified.isoformat() if last_notified else None
    state['numbers_were_available'] = numbers_were_available
    save_state()
    print(json.dumps({'available': False, 'count': 0}))
    exit(0)

info(f"Found {count} numbers (price: {price})")

# Decide whether to notify/purchase based on cooldown
now = datetime.now()
can_notify = False
if last_notified is None:
    can_notify = True
else:
    elapsed = (now - last_notified).total_seconds()
    if numbers_were_available:
        # if numbers were available previously, we wait COOLDOWN_AFTER_NOTIFICATION then if still available notify and then next wait RECHECK_INTERVAL
        if elapsed >= COOLDOWN_AFTER_NOTIFICATION:
            can_notify = True
    else:
        # numbers became available now and no prior notification -> notify
        can_notify = True

purchased = []

if can_notify:
    # Optionally purchase
    if AUTO_PURCHASE:
        info(f"AUTO_PURCHASE enabled: attempting to buy {PURCHASE_QUANTITY} numbers")
        for i in range(PURCHASE_QUANTITY):
            try:
                url = f"{ONLINESIM_API_URL}/getNum.php"
                params = {'apikey': ONLINESIM_API_KEY, 'service': SERVICE, 'country': COUNTRY}
                r = requests.get(url, params=params, timeout=20)
                r.raise_for_status()
                resp = r.json()
                if isinstance(resp, dict) and 'tzid' in resp and 'number' in resp:
                    entry = {'tzid': resp.get('tzid'), 'number': resp.get('number'), 'price': resp.get('price', 'N/A'), 'purchased_at': now.isoformat()}
                    purchased.append(entry)
                    info(f"Purchased: {entry['number']} (tzid={entry['tzid']})")
                else:
                    info(f"Purchase failed or no number: {resp}")
                    # if NO_NUMBER stop attempts
                    if isinstance(resp, dict) and resp.get('response') == 'NO_NUMBER':
                        break
            except Exception as e:
                info(f"Purchase error: {e}")
                break

    # Send email (even if no purchases succeeded, because user wanted notification)
    if EMAIL_ENABLED and SENDER_EMAIL and SENDER_PASSWORD and RECIPIENT_EMAIL:
        try:
            subj = f"{ '✅ Purchased' if purchased else '🎉 Available'} {SERVICE.title()} numbers in country {COUNTRY}"
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subj
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECIPIENT_EMAIL

            text = f"{subj}\n\nCount: {count}\nPrice: {price}\nTime: {now.isoformat()}\n"
            if purchased:
                text += "\nPurchased:\n"
                for p in purchased:
                    text += f"- {p['number']} (tzid={p['tzid']}) price={p['price']}\n"

            part1 = MIMEText(text, 'plain')
            msg.attach(part1)

            s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            s.starttls()
            s.login(SENDER_EMAIL, SENDER_PASSWORD)
            s.send_message(msg)
            s.quit()
            info("Email sent")
        except Exception as e:
            info(f"Email error: {e}")
    else:
        info("Email not sent (disabled or missing credentials)")

    # update state
    last_notified = now
    numbers_were_available = True
    state['last_notification_time'] = last_notified.isoformat()
    state['numbers_were_available'] = numbers_were_available
    save_state()

    # Save purchases to purchases file if any
    if purchased:
        allp = []
        if PURCHASES_FILE.exists():
            try:
                allp = json.loads(PURCHASES_FILE.read_text())
            except Exception:
                allp = []
        allp.extend(purchased)
        PURCHASES_FILE.write_text(json.dumps(allp, indent=2))

    print(json.dumps({'available': True, 'count': count, 'purchased': len(purchased)}))
    exit(0)

else:
    info("In cooldown, not notifying")
    # If in cooldown, just update that numbers still available
    numbers_were_available = True
    state['numbers_were_available'] = numbers_were_available
    save_state()
    print(json.dumps({'available': True, 'count': count, 'purchased': 0, 'cooldown': True}))
    exit(0)
