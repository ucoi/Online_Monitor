# OnlineSim Monitor

Automatically monitor OnlineSim for Hungarian Foodora phone numbers and receive email notifications when they become available.

## Features

- 🔍 Monitors OnlineSim API for Hungarian numbers for Foodora
- 📧 Sends email notifications when numbers are available
- 📊 Logging to both console and file
- ⚙️ Configurable check intervals
- 🔄 Continuous monitoring

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Settings

Edit `config.py` and update the following:

**OnlineSim API:**

- `ONLINESIM_API_KEY`: Your OnlineSim API key (get it from https://onlinesim.io/profile)

**Email Settings (for Gmail):**

- `SENDER_EMAIL`: Your Gmail address
- `SENDER_PASSWORD`: Your Gmail App Password (see instructions below)
- `RECIPIENT_EMAIL`: Email where you want to receive notifications

**Monitoring:**

- `CHECK_INTERVAL`: How often to check (in seconds, default: 300 = 5 minutes)

### 3. Gmail App Password Setup

If using Gmail, you need to create an App Password:

1. Go to your Google Account settings
2. Navigate to Security
3. Enable 2-Factor Authentication if not already enabled
4. Go to "App passwords"
5. Create a new app password for "Mail"
6. Copy the generated password to `SENDER_PASSWORD` in `config.py`

### 4. Other Email Providers

For other email providers, update these settings in `config.py`:

- `SMTP_SERVER`: Your SMTP server (e.g., "smtp.outlook.com" for Outlook)
- `SMTP_PORT`: SMTP port (usually 587 for TLS)

## Usage

### Run the Monitor

```bash
python monitor.py
```

The monitor will:

- Check OnlineSim every 5 minutes (configurable)
- Log activity to both console and `monitor.log`
- Send email notifications when Hungarian Foodora numbers are available

### Stop the Monitor

Press `Ctrl+C` to stop monitoring.

### Run in Background (macOS/Linux)

To run the monitor in the background:

```bash
nohup python monitor.py > output.log 2>&1 &
```

To stop it later:

```bash
pkill -f monitor.py
```

## Customization

### Change Service or Country

Edit `config.py`:

- `SERVICE`: Change to another service name (e.g., "uber", "whatsapp")
- `COUNTRY`: Change country code (e.g., 1 for USA, 44 for UK, 36 for Hungary)

### Adjust Check Frequency

Edit `CHECK_INTERVAL` in `config.py`:

- 300 = 5 minutes
- 600 = 10 minutes
- 60 = 1 minute (not recommended - may hit rate limits)

## Troubleshooting

### API Errors

- Verify your API key is correct
- Check your OnlineSim account has sufficient balance
- Ensure the service name and country code are correct

### Email Not Sending

- Check your email credentials
- Verify App Password is created (for Gmail)
- Check spam folder for notifications
- Review `monitor.log` for error messages

### No Numbers Found

- Numbers may genuinely not be available
- Try different check intervals
- Verify the service name matches OnlineSim's service list

## Logs

All activity is logged to:

- Console (standard output)
- `monitor.log` file

## OnlineSim API Reference

- API Documentation: https://onlinesim.io/docs
- Get API Key: https://onlinesim.io/profile
- Country Codes: 36 = Hungary

## License

MIT License - Feel free to modify and use as needed.
