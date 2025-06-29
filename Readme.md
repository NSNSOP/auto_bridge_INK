git clone https://github.com/NSNSOP/auto_bridge_INK
cd auto_bridge_INK

# Automated Swap & Rebalancing Bot

## Description

This bot is designed to perform automated trading cycles on EVM-compatible chains. It operates in two main phases:

1.  **Spending Phase**: Automatically swaps a randomized amount of native currency (ETH) for various pre-configured ERC20 tokens.
2.  **Rebalancing Phase**: Swaps a configurable percentage of the acquired ERC20 tokens back to the native currency (ETH) to refuel for the next cycle.

The bot includes safety features, such as a minimum balance threshold, to prevent it from running out of gas funds.

## Features

* **Automated Cycles**: Runs continuously in a spending and rebalancing loop.
* **Randomized Behavior**: Uses random amounts, token selections, and delays to simulate more human-like activity.
* **On-Demand Rebalancing**: If the native currency balance drops below a safe threshold, the bot will automatically attempt to swap tokens back to refuel.
* **Highly Configurable**: All major parameters (swap amounts, delays, token lists, safety thresholds) can be easily edited in the `config.py` file.

## Prerequisites

* Python 3.8 or higher
* `pip` package manager

## Installation & Setup

Follow these steps to set up and run the bot in a clean environment.

**1. Create a Virtual Environment**

It is highly recommended to run the bot in a dedicated virtual environment.

```bash
# Create the virtual environment folder
python3 -m venv venv

# Activate the environment (on Linux/macOS)
source venv/bin/activate

2. Install Dependencies

Install all the required Python libraries using the requirements.txt file.

Bash

pip install -r requirements.txt
3. Configure the Bot

All settings are managed in the config.py file.

Open the config.py file with a text editor.

IMPORTANT: You must replace the placeholder 0xPrivatekeyHere with your actual wallet private key. The bot will not run without it.

Python

# config.py
PRIVATE_KEY = "0xYourActualPrivateKeyGoesHere"
Adjust other parameters like MIN_ETH_AMOUNT, MAX_SWAP_COUNT, TOKEN_LIST, etc., to fit your strategy.

Running the Bot
Once the setup is complete, you can run the bot with the following command:

Bash

python3 auto_bridge.py
The bot will start running and log all its actions to the terminal with timestamps.

Running as a Background Process

For long-term, continuous operation (e.g., on a server), it is recommended to run the script using a terminal multiplexer like screen or tmux. This ensures the bot keeps running even after you close the terminal.

Example using screen:

Bash

# Start a new screen session named 'swapbot'
screen -S swapbot

# Run the bot inside the new session
python3 auto_bridge.py

# Detach from the session by pressing Ctrl+A then D. The bot will keep running.
# To re-attach to the session later, use: screen -r swapbot
⚠️ Disclaimer
RISK OF LOSS: This is an automated trading bot that interacts with real cryptocurrency. Bugs, configuration errors, or market volatility can lead to financial loss. Use it at your own risk.

SECURITY: Your private key gives full control over your wallet. Handle the config.py file with extreme care and never share it or commit it to a public repository. It is highly recommended to use a new, dedicated wallet for this bot with a limited amount of funds.
