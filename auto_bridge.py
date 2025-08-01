import time
import random
import json
from datetime import datetime
from web3 import Web3
import requests
import config

def setup():
    """Mempersiapkan koneksi Web3 dan memuat akun dari private key."""
    w3 = Web3(Web3.HTTPProvider(config.WEB3_PROVIDER_URL))
    if not w3.is_connected():
        log_message("ERROR: Gagal terhubung ke provider Web3.")
        return None, None
    try:
        account = w3.eth.account.from_key(config.PRIVATE_KEY)
        return w3, account
    except Exception as e:
        log_message(f"ERROR: Gagal memuat dompet. Periksa config.py. Detail: {e}")
        return None, None

def log_message(message):
    """Mencetak pesan dengan timestamp untuk logging."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def get_api_quote(w3, from_token, to_token, amount_in_wei, user_address, is_reversal=False):
    """
    Mendapatkan quote dari API. Jika reversal, kembalikan semua langkah (steps).
    """
    log_message(f"Meminta quote dari API untuk {from_token} -> {to_token}...")
    url = "https://api.relay.link/quote"
    headers = {"accept": "application/json", "content-type": "application/json"}
    payload = {
        "user": user_address, "originChainId": 57073, "destinationChainId": 57073,
        "originCurrency": from_token, "destinationCurrency": to_token, "recipient": user_address,
        "tradeType": "EXACT_INPUT", "amount": str(amount_in_wei),
        "referrer": "inkonchain.com", "useExternalLiquidity": False
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        quote_data = response.json()
        
        if is_reversal:
            return quote_data.get('steps', [])

        return [quote_data['steps'][0]]
        
    except Exception as e:
        log_message(f"   ERROR: Gagal mendapatkan quote dari Server: {e}")
        return None

def execute_transaction(w3, account, tx_details):
    """
    Menandatangani dan mengeksekusi transaksi.
    Jika API tidak memberikan gas limit, skrip akan mengestimasi sendiri.
    """
    try:
        tx_to_sign = {
            'to': Web3.to_checksum_address(tx_details['to']),
            'from': account.address,
            'data': tx_details['data'],
            'value': int(tx_details.get('value', 0)),
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': w3.eth.chain_id
        }

        if 'gas' in tx_details and tx_details['gas'] is not None:
            tx_to_sign['gas'] = int(tx_details['gas'])
        else:
            log_message("   PERINGATAN: API tidak memberikan gas limit. Mengestimasi secara manual...")
            estimated_gas = w3.eth.estimate_gas(tx_to_sign)
            tx_to_sign['gas'] = int(estimated_gas * 1.2)

        if 'maxFeePerGas' in tx_details and 'maxPriorityFeePerGas' in tx_details:
             tx_to_sign['maxFeePerGas'] = int(tx_details['maxFeePerGas'])
             tx_to_sign['maxPriorityFeePerGas'] = int(tx_details['maxPriorityFeePerGas'])
        else:
            latest_block = w3.eth.get_block('latest')
            base_fee = latest_block['baseFeePerGas']
            max_priority_fee = w3.eth.max_priority_fee
            tx_to_sign['maxFeePerGas'] = (2 * base_fee) + max_priority_fee
            tx_to_sign['maxPriorityFeePerGas'] = max_priority_fee

        log_message(f"--> Menandatangani transaksi ke {tx_to_sign['to']}...")
        signed_tx = w3.eth.account.sign_transaction(tx_to_sign, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        log_message(f"--> Transaksi terkirim. Hash: {tx_hash.hex()}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=360)
        
        if tx_receipt.status == 1:
            log_message("--> Transaksi SUKSES.")
            return True
        else:
            log_message("--> Transaksi GAGAL.")
            return False
    except Exception as e:
        log_message(f"   ERROR saat eksekusi transaksi: {e}")
        return False

def get_token_balance(w3, account, token_info):
    """Mendapatkan saldo token ERC20 dalam unit terkecilnya (wei)."""
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_info['address']), abi=config.ERC20_ABI)
    return token_contract.functions.balanceOf(account.address).call()

def trigger_emergency_rebalance(w3, account):
    """
    Mencoba menjual SEMUA saldo dari SATU token (non-WETH) untuk mengisi ulang ETH.
    Berhenti setelah penjualan pertama berhasil untuk efisiensi.
    """
    log_message("!!! MEMULAI PROSES ISI ULANG ETH DARURAT !!!")
    
    for symbol, info in config.TOKEN_LIST.items():
        if symbol == 'WETH':
            continue

        balance_wei = get_token_balance(w3, account, info)
        if balance_wei > 0:
            human_readable_balance = balance_wei / (10**info['decimals'])
            log_message(f"-> Target Rebalance: Mencoba menjual {human_readable_balance:.6f} {symbol}...")
            
            transaction_steps = get_api_quote(
                w3, info['address'], "0x0000000000000000000000000000000000000000",
                balance_wei, account.address, is_reversal=True
            )

            if not transaction_steps:
                log_message(f"--> Gagal mendapatkan rencana transaksi untuk {symbol}. Mencoba token lain...")
                continue

            all_steps_succeeded = True
            for i, step in enumerate(transaction_steps):
                log_message(f"   Mengeksekusi Langkah #{i + 1}: {step.get('description', step.get('id', ''))}")
                step_data = step['items'][0]['data']
                
                if not execute_transaction(w3, account, step_data):
                    log_message(f"--> GAGAL pada langkah {step.get('id', '')} untuk {symbol}.")
                    all_steps_succeeded = False
                    break 
                
                if i < len(transaction_steps) - 1:
                    log_message("   Jeda sejenak sebelum langkah berikutnya...")
                    time.sleep(15)

            if all_steps_succeeded:
                log_message(f"Isi ulang ETH berhasil dengan menjual {symbol}.")
                return True
            else:
                log_message(f"Gagal menjual {symbol}. Mencoba token berikutnya jika ada.")
    
    log_message("Tidak ada token yang bisa dijual untuk mengisi ulang ETH setelah mencoba semua opsi.")
    return False

def run_swap_cycle(w3, account):
    """
    Fungsi utama yang menjalankan siklus swap dengan logika pengisian ulang darurat.
    """
    swap_target = random.randint(config.MIN_SWAP_COUNT, config.MAX_SWAP_COUNT)
    log_message(f"Memulai SIKLUS SWAP, menargetkan {swap_target} transaksi.")
    
    for i in range(swap_target):
        log_message(f"--- Memproses Swap #{i + 1}/{swap_target} ---")
        
        eth_balance = w3.eth.get_balance(account.address)
        if eth_balance < w3.to_wei(config.MIN_ETH_BALANCE_THRESHOLD, 'ether'):
            log_message(f"PERINGATAN: Saldo ETH ({w3.from_wei(eth_balance, 'ether')} ETH) rendah. Memicu isi ulang darurat...")
            
            refuel_success = trigger_emergency_rebalance(w3, account)
            
            eth_balance_after_refuel = w3.eth.get_balance(account.address)
            if not refuel_success or eth_balance_after_refuel < w3.to_wei(config.MIN_ETH_BALANCE_THRESHOLD, 'ether'):
                log_message("KRITIS: Gagal mengisi ulang ETH atau saldo masih kurang. Menghentikan siklus saat ini.")
                break
            else:
                log_message("Isi ulang berhasil, melanjutkan siklus.")
        
        target_symbol = random.choice(list(config.TOKEN_LIST.keys()))
        amount_to_swap = random.uniform(config.MIN_ETH_AMOUNT, config.MAX_ETH_AMOUNT)
        amount_wei = w3.to_wei(amount_to_swap, 'ether')
        log_message(f"Eksekusi swap: {amount_to_swap:.8f} ETH ke {target_symbol}...")
        
        quote_steps = get_api_quote(
            w3, "0x0000000000000000000000000000000000000000",
            config.TOKEN_LIST[target_symbol]['address'],
            amount_wei, account.address, is_reversal=False
        )
        if quote_steps:
            execute_transaction(w3, account, quote_steps[0]['items'][0]['data'])
        
        if i < swap_target - 1:
             delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
             log_message(f"Jeda acak: Menunggu {delay/60:.2f} menit...")
             time.sleep(delay)
             
    log_message(f"Siklus {swap_target} swap telah selesai.")

def main():
    """Fungsi utama untuk menjalankan siklus bot tanpa henti."""
    log_message("="*40)
    log_message("   Memulai Ultimate Swap Bot v2")
    log_message("="*40)
    w3, account = setup()
    if not (w3 and account):
        return
    while True:
        run_swap_cycle(w3, account)
        log_message("Siklus utama selesai. Menunggu 1 jam sebelum memulai siklus besar berikutnya.")
        time.sleep(3600)

if __name__ == "__main__":
    main()
