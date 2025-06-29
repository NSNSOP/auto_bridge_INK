import time
import random
import json
from datetime import datetime
from web3 import Web3
import requests

import config


def setup():
    w3 = Web3(Web3.HTTPProvider(config.WEB3_PROVIDER_URL))
    if not w3.is_connected():
        log_message("ERROR: ERROR: Failed to connect to Web3 provider.")
        return None, None
    try:
        account = w3.eth.account.from_key(config.PRIVATE_KEY)
        return w3, account
    except Exception as e:
        log_message(f"ERROR: ERROR: Failed to load wallet. Periksa config.py. Detail: {e}")
        return None, None

def log_message(message):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def get_api_quote(w3, from_token, to_token, amount_in_wei, user_address):
    log_message(f"Requesting quote from API for {from_token} -> {to_token}...")
    url = "https://api.relay.link/quote"
    headers = {"accept": "application/json", "content-type": "application/json"}
    payload = { "user": user_address, "originChainId": 57073, "destinationChainId": 57073, "originCurrency": from_token, "destinationCurrency": to_token, "recipient": user_address, "tradeType": "EXACT_INPUT", "amount": str(amount_in_wei), "referrer": "inkonchain.com", "useExternalLiquidity": False }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        quote_data = response.json()
        tx_data = quote_data['steps'][0]['items'][0]['data']
        return {
            "to": Web3.to_checksum_address(tx_data['to']), "data": tx_data['data'], "value": int(tx_data['value']), "gas": int(tx_data['gas']),
            "maxFeePerGas": int(tx_data.get('maxFeePerGas', '5000000000')), "maxPriorityFeePerGas": int(tx_data.get('maxPriorityFeePerGas', '1000000000'))
        }
    except Exception as e:
        log_message(f"ERROR: Failed to get quote from API: {e}")
        return None


def execute_transaction(w3, account, tx_details):
    try:
        final_tx = {
            'to': tx_details['to'], 'from': account.address, 'data': tx_details['data'], 'value': tx_details['value'], 'gas': tx_details['gas'],
            'maxFeePerGas': tx_details['maxFeePerGas'], 'maxPriorityFeePerGas': tx_details['maxPriorityFeePerGas'],
            'nonce': w3.eth.get_transaction_count(account.address), 'chainId': w3.eth.chain_id
        }
        log_message(f"Signing transaction to: {final_tx['to']}...")
        signed_tx = w3.eth.account.sign_transaction(final_tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        log_message(f"Transaction sent. Hash: {tx_hash.hex()}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=360)
        
        if tx_receipt.status == 1:
            log_message("-> Transaction SUCCESS.")
            return True
        else:
            log_message("-> Transaction FAILED.")
            return False
    except Exception as e:
        log_message(f"ERROR during transaction execution: {e}")
        return False

def get_token_balance(w3, account, token_info):
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_info['address']), abi=config.ERC20_ABI)
    return token_contract.functions.balanceOf(account.address).call()

def approve_token(w3, account, token_address, spender_address, amount):
    log_message(f"Approving token for {spender_address}...")
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=config.ERC20_ABI)
    tx = token_contract.functions.approve(spender_address, amount).build_transaction({
        'from': account.address, 'nonce': w3.eth.get_transaction_count(account.address), 'gas': 100000,
        'maxFeePerGas': w3.to_wei('10', 'gwei'), 'maxPriorityFeePerGas': w3.to_wei('1', 'gwei')
    })
    return execute_transaction(w3, account, tx)


def trigger_emergency_rebalance(w3, account):
    Mencari satu token yang memiliki saldo dan menukarnya ke ETH untuk isi ulang.
    Mengembalikan True jika berhasil, False jika gagal.
    log_message("Looking for token to sell back to ETH...")
    eth_address = "0x0000000000000000000000000000000000000000"

    token_items = list(config.TOKEN_LIST.items())
    random.shuffle(token_items)

    for symbol, info in token_items:
        if symbol == 'WETH': continue # WETH sebaiknya di-unwrap, bukan di-swap
        
        balance = get_token_balance(w3, account, info)
        if balance > 0:
            amount_to_swap = int(balance * config.REBALANCE_PERCENTAGE)
            human_readable_balance = amount_to_swap / (10**info['decimals'])
            log_message(f"Found {symbol} with balance. Trying to sell {human_readable_balance:.6f} {symbol} to refill ETH.")
            
            quote = get_api_quote(w3, info['address'], eth_address, amount_to_swap, account.address)
            if quote:
                approval_ok = approve_token(w3, account, info['address'], quote['to'], amount_to_swap)
                if approval_ok:
                    log_message("Approval success. Proceeding with reversal swap.")
                    time.sleep(20)
                    swap_ok = execute_transaction(w3, account, quote)
                    if swap_ok:
                        log_message("ETH refill success.")
                        return True # Berhasil, keluar dari fungsi
            log_message(f"Failed to rebalance for {symbol}, trying next token...")

    log_message("No token available to sell for ETH refill.")
    return False # Gagal menemukan token untuk di-rebalance

def run_swap_cycle(w3, account):
    Fungsi utama yang menjalankan siklus swap dengan logika pengisian ulang darurat.
    swap_target = random.randint(config.MIN_SWAP_COUNT, config.MAX_SWAP_COUNT)
    log_message(f"Starting SWAP CYCLE, targeting {swap_target} transaksi.")

    for i in range(swap_target):
        log_message(f"--- Processing Swap #{i+1}/{swap_target} ---")
        
        eth_balance = w3.eth.get_balance(account.address)
        if eth_balance < w3.to_wei(config.MIN_ETH_BALANCE_THRESHOLD, 'ether'):
            log_message(f"WARNING: ETH balance ({w3.from_wei(eth_balance, 'ether')} ETH) is low. Triggering emergency refill...")
            
            refuel_success = trigger_emergency_rebalance(w3, account)
        eth_balance = w3.eth.get_balance(account.address)
        if eth_balance < w3.to_wei(config.MIN_ETH_BALANCE_THRESHOLD, 'ether'):
            log_message("BALANCE STILL LOW: Isi ulang ETH tidak mencukupi. Stopping cycle.")
            break
            
            if not refuel_success:
                log_message("CRITICAL: Failed to refill ETH. Cannot continue cycle. Bot will wait before starting next cycle.")
                break # Keluar dari loop for, menghentikan siklus ini
            else:
                log_message("Refill successful, continuing cycle.")
        
        target_symbol = random.choice(list(config.TOKEN_LIST.keys()))
        amount_to_swap = random.uniform(config.MIN_ETH_AMOUNT, config.MAX_ETH_AMOUNT)
        amount_wei = w3.to_wei(amount_to_swap, 'ether')

        log_message(f"Executing swap: {amount_to_swap:.8f} ETH ke {target_symbol}...")
        
        quote = get_api_quote(
            w3, "0x0000000000000000000000000000000000000000",
            config.TOKEN_LIST[target_symbol]['address'],
            amount_wei, account.address
        )
        if quote:
            execute_transaction(w3, account, quote)

        if i < swap_target - 1: # Jangan menunggu setelah swap terakhir
             delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
             log_message(f"Random delay: Waiting {delay/60:.2f} minutes...")
             time.sleep(delay)

    log_message(f"Cycle {swap_target} swaps completed.")


def main():
    log_message("="*40)
    log_message("   Launching Ultimate Swap Bot v2")
    log_message("="*40)
    w3, account = setup()
    if not (w3 and account):
        return

    while True:
        run_swap_cycle(w3, account)
        log_message("Cycle utama selesai. Waiting 1 hour before starting next major cycle.")
        time.sleep(3600) # Tunggu 1 jam sebelum memulai siklus 100-150 swap lagi

if __name__ == "__main__":
    main()
