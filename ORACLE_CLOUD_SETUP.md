# Oracle Cloud Free Tier Setup Guide

Deploy your OnlineSim Monitor to Oracle Cloud's Always Free tier for 24/7 monitoring at **zero cost**.

## Step 1: Create Oracle Cloud Account

1. Go to https://www.oracle.com/cloud/free/
2. Click **Start for Free**
3. Fill in your details (requires credit card for verification, but won't be charged)
4. Complete email verification

## Step 2: Create a Free VM Instance

1. **Login** to Oracle Cloud Console: https://cloud.oracle.com
2. Click **Create a VM Instance** (or go to: Compute → Instances → Create Instance)

3. **Configure the Instance:**
   - **Name**: `onlinesim-monitor`
   - **Placement**: Leave default (or choose closest region)
   - **Image**: `Ubuntu 22.04` (or latest Ubuntu)
   - **Shape**:
     - Click "Change Shape"
     - Select **"Ampere" (ARM-based)**
     - Choose **VM.Standard.A1.Flex**
     - Set **1 OCPU** and **6 GB RAM** (Always Free limits)
4. **Networking** (Very Important):

   - Keep "Assign public IPv4 address" ✅ checked
   - Note: You don't need to open any ports for this monitor

5. **SSH Keys**:
   - If on Mac/Linux: Generate SSH key:
     ```bash
     ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle_cloud_keyf
     ```
   - Click "Paste public keys"
   - Paste content of `~/.ssh/oracle_cloud_key.pub`
6. Click **Create**

7. Wait 1-2 minutes for instance to provision

8. **Note the Public IP Address** shown on the instance details page

## Step 3: Connect to Your VM

```bash
# Replace <PUBLIC_IP> with your instance's IP address
ssh -i ~/.ssh/oracle_cloud_key ubuntu@<PUBLIC_IP>
```

**First time**: Type `yes` when asked about host authenticity

## Step 4: Setup Python Environment on VM

Once connected to the VM:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Create project directory
mkdir ~/onlinesim-monitor
cd ~/onlinesim-monitor
```

## Step 5: Upload Your Code to VM

**Option A: From your Mac (in a NEW terminal, not SSH):**

```bash
# Navigate to your project folder
cd /private/tmp/onlinesim-monitor/OnlineSim

# Upload files to Oracle VM (replace <PUBLIC_IP>)
scp -i ~/.ssh/oracle_cloud_key \
    config.py monitor.py requirements.txt \
    ubuntu@<PUBLIC_IP>:~/onlinesim-monitor/
```

**Option B: Manually create files on VM:**

```bash
# In SSH session, create each file
nano ~/onlinesim-monitor/config.py
# Paste your config.py content, then Ctrl+X, Y, Enter

nano ~/onlinesim-monitor/monitor.py
# Paste your monitor.py content, then Ctrl+X, Y, Enter

nano ~/onlinesim-monitor/requirements.txt
# Paste: requests>=2.31.0
# Then Ctrl+X, Y, Enter
```

## Step 6: Install Dependencies and Test

```bash
cd ~/onlinesim-monitor

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/python3

# Install requirements
pip install -r requirements.txt

# Test the monitor (Ctrl+C to stop after confirming it works)
python monitor.py
```

## Step 7: Run Monitor 24/7 with Systemd (Recommended)

Create a systemd service to auto-start and auto-restart the monitor:

```bash
# Create service file
sudo nano /etc/systemd/system/onlinesim-monitor.service
```

**Paste this content:**

```ini
[Unit]
Description=OnlineSim Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/onlinesim-monitor
ExecStart=/home/ubuntu/onlinesim-monitor/.venv/bin/python monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Save:** Ctrl+X, Y, Enter

**Enable and start the service:**

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable onlinesim-monitor

# Start the service now
sudo systemctl start onlinesim-monitor

# Check status
sudo systemctl status onlinesim-monitor
```

## Step 8: Monitor and Manage

### Check if it's running:

```bash
sudo systemctl status onlinesim-monitor
```

### View live logs:

```bash
sudo journalctl -u onlinesim-monitor -f
```

### View log file:

```bash
tail -f ~/onlinesim-monitor/monitor.log
```

### Check purchased numbers:

```bash
cat ~/onlinesim-monitor/purchased_numbers.json
```

### Stop the monitor:

```bash
sudo systemctl stop onlinesim-monitor
```

### Restart the monitor:

```bash
sudo systemctl restart onlinesim-monitor
```

### Update config (after editing):

```bash
# Edit config
nano ~/onlinesim-monitor/config.py

# Restart to apply changes
sudo systemctl restart onlinesim-monitor
```

## Alternative: Run with Screen (Simpler but less robust)

If you don't want to use systemd:

```bash
# Install screen
sudo apt install screen -y

# Start a screen session
screen -S monitor

# Run the monitor
cd ~/onlinesim-monitor
python monitor.py

# Detach: Press Ctrl+A then D

# Reattach later:
screen -r monitor

# List sessions:
screen -ls
```

## Troubleshooting

### Can't connect via SSH?

- Check Security List rules in Oracle Cloud Console
- Ensure your IP isn't blocked by firewall
- Verify you're using the correct SSH key

### Monitor not starting?

```bash
# Check service logs
sudo journalctl -u onlinesim-monitor -n 50

# Check file permissions
ls -la ~/onlinesim-monitor/

# Test manually
cd ~/onlinesim-monitor
source .venv/bin/activate
python monitor.py
```

### Email not sending?

- Verify Gmail App Password in `config.py`
- Check logs for specific error messages
- Test internet connectivity: `ping google.com`

## Updating Your Monitor

When you make changes locally:

```bash
# From your Mac
cd /private/tmp/onlinesim-monitor/OnlineSim
scp -i ~/.ssh/oracle_cloud_key monitor.py ubuntu@<PUBLIC_IP>:~/onlinesim-monitor/

# Then restart on VM
ssh -i ~/.ssh/oracle_cloud_key ubuntu@<PUBLIC_IP>
sudo systemctl restart onlinesim-monitor
```

## Cost

✅ **$0/month** with Oracle's Always Free tier:

- 1 ARM-based VM (up to 4 OCPUs and 24 GB RAM total across all instances)
- 200 GB block storage
- 10 TB outbound data transfer per month

This is **permanently free**, not a trial!

## Summary

Your monitor is now running 24/7 on Oracle Cloud at zero cost! It will:

- ✅ Check for Hungarian Foodora numbers every 60 seconds
- ✅ Automatically purchase 2 numbers when available
- ✅ Email you the purchased numbers
- ✅ Auto-restart if it crashes
- ✅ Start automatically after VM reboots
- ✅ Save all purchased numbers to JSON file

🎉 **You're all set!**
