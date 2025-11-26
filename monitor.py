#!/usr/bin/env python3
"""
OnlineSim Monitor - Check for Hungarian Foodora numbers and send email alerts
"""

import requests
import smtplib
import time
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import *


class OnlineSimMonitor:
    def __init__(self):
        self.setup_logging()
        self.last_notification_time = None
        self.numbers_were_available = False  # Track if numbers were available in last check
        self.purchased_numbers = []  # Track purchased numbers in this session
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def check_numbers_available(self):
        """Check if Hungarian Foodora numbers are available"""
        try:
            # OnlineSim API endpoint to get number statistics/availability
            url = f"{ONLINESIM_API_URL}/getNumbersStats.php"
            
            params = {
                'apikey': ONLINESIM_API_KEY,
                'country': COUNTRY,
                'service': SERVICE
            }
            
            country_name = "Hungary" if COUNTRY == 36 else f"Country {COUNTRY}"
            self.logger.info(f"Checking OnlineSim for {SERVICE} numbers in {country_name} (country code: {COUNTRY})")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if numbers are available
            # The API returns: {"services": {"service_foodora": {"count": 2564, "price": 0.19, ...}}}
            if isinstance(data, dict) and 'services' in data:
                service_key = f"service_{SERVICE}"
                if service_key in data['services']:
                    service_data = data['services'][service_key]
                    count = service_data.get('count', 0)
                    price = service_data.get('price', 'N/A')
                    
                    if count > 0:
                        self.logger.info(f"✓ Found {count} {SERVICE.title()} number(s) available! (Price: ${price})")
                        return True, count, service_data
                    else:
                        self.logger.info("No numbers available at the moment")
                        return False, 0, None
                else:
                    self.logger.warning(f"Service '{SERVICE}' not found in response")
                    return False, 0, None
            else:
                self.logger.warning(f"Unexpected API response format: {data}")
                return False, 0, None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error checking OnlineSim API: {e}")
            return False, 0, None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False, 0, None
    
    def purchase_numbers(self, quantity=2):
        """Purchase numbers from OnlineSim"""
        if not AUTO_PURCHASE:
            self.logger.info("Auto-purchase is disabled")
            return []
        
        purchased = []
        
        try:
            self.logger.info(f"Attempting to purchase {quantity} number(s)...")
            
            for i in range(quantity):
                url = f"{ONLINESIM_API_URL}/getNum.php"
                params = {
                    'apikey': ONLINESIM_API_KEY,
                    'service': SERVICE,
                    'country': COUNTRY
                }
                
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # Check if purchase was successful
                if isinstance(data, dict):
                    if 'tzid' in data and 'number' in data:
                        # Successful purchase
                        number_info = {
                            'tzid': data.get('tzid'),
                            'number': data.get('number'),
                            'country': data.get('country'),
                            'service': SERVICE,
                            'price': data.get('price', 'N/A')
                        }
                        purchased.append(number_info)
                        self.logger.info(f"✓ Successfully purchased number {i+1}/{quantity}: {number_info['number']} (TxID: {number_info['tzid']})")
                    elif data.get('response') == 'NO_NUMBER':
                        self.logger.warning(f"⚠ Number {i+1}/{quantity}: No numbers available to purchase (may have sold out)")
                        break  # Stop trying if no numbers available
                    elif 'msg' in data:
                        error_msg = data.get('msg', 'Unknown error')
                        self.logger.error(f"Failed to purchase number {i+1}/{quantity}: {error_msg}")
                    else:
                        self.logger.error(f"Failed to purchase number {i+1}/{quantity}: Unexpected response - {data}")
                
                # Small delay between purchases
                if i < quantity - 1:
                    time.sleep(1)
            
            if purchased:
                self.purchased_numbers.extend(purchased)
                self.logger.info(f"✓ Successfully purchased {len(purchased)}/{quantity} number(s)")
                
                # Save purchased numbers to file
                self.save_purchased_numbers(purchased)
            
            return purchased
            
        except Exception as e:
            self.logger.error(f"Error during purchase: {e}")
            return purchased
    
    def save_purchased_numbers(self, purchased):
        """Save purchased numbers to a file for reference"""
        try:
            import json
            from pathlib import Path
            
            purchases_file = Path("purchased_numbers.json")
            
            # Load existing purchases
            all_purchases = []
            if purchases_file.exists():
                with open(purchases_file, 'r') as f:
                    all_purchases = json.load(f)
            
            # Add new purchases with timestamp
            for num in purchased:
                num['purchased_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                all_purchases.append(num)
            
            # Save back to file
            with open(purchases_file, 'w') as f:
                json.dump(all_purchases, f, indent=2)
            
            self.logger.info(f"Saved purchase details to {purchases_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving purchased numbers: {e}")
    
    def send_email_notification(self, count, data, purchased_numbers=None):
        """Send email notification when numbers are available"""
        if not EMAIL_ENABLED:
            self.logger.info("Email notifications disabled")
            return False
            
        try:
            # Extract price and country info
            price = data.get('price', 'N/A')
            country_name = "Hungary" if COUNTRY == 36 else "Ukraine" if COUNTRY == 380 else f"Country {COUNTRY}"
            
            # Create message
            msg = MIMEMultipart('alternative')
            
            if purchased_numbers:
                msg['Subject'] = f'✅ Purchased {len(purchased_numbers)} {SERVICE.title()} Number(s) in {country_name}!'
            else:
                msg['Subject'] = f'🎉 {SERVICE.title()} Numbers Available in {country_name}! ({count} found)'
            
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECIPIENT_EMAIL
            
            # Build purchased numbers info
            purchased_info_text = ""
            purchased_info_html = ""
            
            if purchased_numbers:
                purchased_info_text = "\n\nPURCHASED NUMBERS:\n" + "="*50 + "\n"
                purchased_info_html = """
    <h3 style="color: #4CAF50;">📱 Purchased Numbers:</h3>
    <table style="border-collapse: collapse; margin: 20px 0; border: 1px solid #ddd;">
      <tr style="background-color: #4CAF50; color: white;">
        <th style="padding: 10px; border: 1px solid #ddd;">#</th>
        <th style="padding: 10px; border: 1px solid #ddd;">Phone Number</th>
        <th style="padding: 10px; border: 1px solid #ddd;">Transaction ID</th>
        <th style="padding: 10px; border: 1px solid #ddd;">Price</th>
      </tr>
"""
                
                for idx, num in enumerate(purchased_numbers, 1):
                    purchased_info_text += f"{idx}. Phone: {num['number']}\n"
                    purchased_info_text += f"   Transaction ID: {num['tzid']}\n"
                    purchased_info_text += f"   Price: ${num['price']}\n\n"
                    
                    purchased_info_html += f"""
      <tr>
        <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{idx}</td>
        <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{num['number']}</td>
        <td style="padding: 10px; border: 1px solid #ddd; font-family: monospace;">{num['tzid']}</td>
        <td style="padding: 10px; border: 1px solid #ddd; color: #4CAF50; font-weight: bold;">${num['price']}</td>
      </tr>
"""
                
                purchased_info_html += """
    </table>
    <p style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107;">
      <strong>📝 Next Steps:</strong><br>
      1. Go to <a href="https://onlinesim.io">OnlineSim.io</a><br>
      2. Check your active numbers<br>
      3. Wait for Foodora SMS codes<br>
      4. Complete your registration
    </p>
"""
            
            # Create email body
            text = f"""
OnlineSim Monitor Alert!

{country_name} numbers for {SERVICE.title()} are now available on OnlineSim!

Count: {count} number(s)
Price: ${price} per number
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Country: {country_name} (code {COUNTRY})
Service: {SERVICE.title()}
{purchased_info_text}
Visit OnlineSim to manage your numbers: https://onlinesim.io

---
This is an automated message from OnlineSim Monitor
            """
            
            html = f"""
<html>
  <body>
    <h2 style="color: #4CAF50;">{'✅ Numbers Purchased!' if purchased_numbers else '🎉 OnlineSim Monitor Alert!'}</h2>
    <p><strong>{country_name} numbers for {SERVICE.title()} are now available!</strong></p>
    
    <table style="border-collapse: collapse; margin: 20px 0;">
      <tr>
        <td style="padding: 8px; font-weight: bold;">Count:</td>
        <td style="padding: 8px;">{count} number(s)</td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Price:</td>
        <td style="padding: 8px; color: #4CAF50; font-weight: bold;">${price} per number</td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Time:</td>
        <td style="padding: 8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Country:</td>
        <td style="padding: 8px;">{country_name} (code {COUNTRY})</td>
      </tr>
      <tr>
        <td style="padding: 8px; font-weight: bold;">Service:</td>
        <td style="padding: 8px;">{SERVICE.title()}</td>
      </tr>
    </table>
    
    {purchased_info_html}
    
    <p>
      <a href="https://onlinesim.io" 
         style="background-color: #4CAF50; color: white; padding: 12px 24px; 
                text-decoration: none; border-radius: 4px; display: inline-block;">
        {'Manage Numbers →' if purchased_numbers else 'Get Number Now →'}
      </a>
    </p>
    
    <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
    <p style="color: #666; font-size: 12px;">This is an automated message from OnlineSim Monitor</p>
  </body>
</html>
            """
            
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            self.logger.info(f"Sending email notification to {RECIPIENT_EMAIL}...")
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg)
            
            self.logger.info("✓ Email notification sent successfully!")
            self.last_notification_time = datetime.now()
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    def run(self):
        """Main monitoring loop"""
        self.logger.info("="*60)
        self.logger.info("OnlineSim Monitor Started")
        self.logger.info(f"Monitoring: {SERVICE} in Hungary (country code: {COUNTRY})")
        self.logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
        self.logger.info("="*60)
        
        try:
            while True:
                available, count, data = self.check_numbers_available()
                
                if available:
                    # Numbers found!
                    if self.last_notification_time is None:
                        # First time finding numbers - purchase and send email
                        purchased = []
                        if AUTO_PURCHASE:
                            purchased = self.purchase_numbers(PURCHASE_QUANTITY)
                        
                        self.send_email_notification(count, data, purchased)
                        self.numbers_were_available = True
                        
                        # Wait 1 hour before checking again
                        self.logger.info(f"Waiting {COOLDOWN_AFTER_NOTIFICATION} seconds (1 hour) before next check...\n")
                        time.sleep(COOLDOWN_AFTER_NOTIFICATION)
                        
                    else:
                        # We already sent an email before
                        time_since_last_email = (datetime.now() - self.last_notification_time).total_seconds()
                        
                        if self.numbers_were_available and time_since_last_email >= COOLDOWN_AFTER_NOTIFICATION:
                            # It's been 1+ hour since last email, and numbers still available
                            purchased = []
                            if AUTO_PURCHASE:
                                purchased = self.purchase_numbers(PURCHASE_QUANTITY)
                            
                            self.send_email_notification(count, data, purchased)
                            
                            # Wait 30 minutes before next check
                            self.logger.info(f"Numbers still available. Waiting {RECHECK_INTERVAL_IF_STILL_AVAILABLE} seconds (30 minutes) before next check...\n")
                            time.sleep(RECHECK_INTERVAL_IF_STILL_AVAILABLE)
                        else:
                            # Already notified recently, just wait
                            self.logger.info(f"Already notified recently. Waiting {CHECK_INTERVAL} seconds before next check...\n")
                            time.sleep(CHECK_INTERVAL)
                else:
                    # No numbers available
                    if self.numbers_were_available:
                        self.logger.info("Numbers no longer available. Resuming normal monitoring.")
                    
                    self.numbers_were_available = False
                    # Back to normal checking interval
                    self.logger.info(f"Waiting {CHECK_INTERVAL} seconds before next check...\n")
                    time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("\nMonitor stopped by user")
        except Exception as e:
            self.logger.error(f"Monitor crashed: {e}")


if __name__ == "__main__":
    monitor = OnlineSimMonitor()
    monitor.run()
