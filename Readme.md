
# Automated Swap & Rebalancing Bot

## Description

This bot is designed to perform automated trading cycles on EVM-compatible chains. It operates in two main phases:

1. **Spending Phase**: Automatically swaps a randomized amount of native currency (ETH) for various pre-configured ERC20 tokens.
2. **Rebalancing Phase**: Swaps a configurable percentage of the acquired ERC20 tokens back to the native currency (ETH) to refuel for the next cycle.

The bot includes safety features, such as a minimum balance threshold, to prevent it from running out of gas funds.

## Features

- **Automated Cycles**: Runs continuously in a spending and rebalancing loop.
- **Randomized Behavior**: Uses random amounts, token selections, and delays to simulate more human-like activity.
- **On-Demand Rebalancing**: If the native currency balance drops below a safe threshold, the bot will automatically attempt to swap tokens back to refuel.
- **Highly Configurable**: All major parameters (swap amounts, delays, token lists, safety thresholds) can be easily edited in the `config.py` file.

## Prerequisites

- Python 3.8 or higher
- `pip` package manager

## Installation & Setup

Follow these steps to set up and run the bot in a clean environment:

### 1. Clone the Repository

```bash
git clone https://github.com/NSNSOP/auto_bridge_INK
cd auto_bridge_INK
```

### 2. Set Up Environment

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure Your Wallet

Edit the `config.py` file and add your private key:

```bash
nano config.py
```

Replace this line:

```python
PRIVATE_KEY = "0xYourActualPrivateKeyGoesHere"
```

### 4. Run the Bot

```bash
screen -S ink_auto_bridge
python3 auto_bridge.py
```

Detach from the session by pressing `Ctrl+A` then `D`. The bot will keep running.  
To re-attach to the session later, use: `screen -r ink_auto_bridge`

## ⚠️ Disclaimer

**RISK OF LOSS**: This is an automated trading bot that interacts with real cryptocurrency. Bugs, configuration errors, or market volatility can lead to financial loss. Use it at your own risk.

**SECURITY**: Your private key gives full control over your wallet. Handle the `config.py` file with extreme care and never share it or commit it to a public repository. It is highly recommended to use a new, dedicated wallet for this bot with a limited amount of funds.
