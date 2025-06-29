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
def get_api_quote(w3, from_token, to_token, amount_in_wei, user_address):
    """Mendapatkan quote dari API Relay untuk semua jenis swap."""
    log_message(f"Meminta quote dari API untuk {from_token} -> {to_token}...")
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
        log_message(f"ERROR: Gagal mendapatkan quote dari API: {e}")
        return None
def execute_transaction(w3, account, tx_details):
    """Menandatangani dan mengeksekusi transaksi yang sudah disiapkan."""
    try:
        final_tx = {
            'to': tx_details['to'], 'from': account.address, 'data': tx_details['data'], 'value': tx_details['value'], 'gas': tx_details['gas'],
            'maxFeePerGas': tx_details['maxFeePerGas'], 'maxPriorityFeePerGas': tx_details['maxPriorityFeePerGas'],
            'nonce': w3.eth.get_transaction_count(account.address), 'chainId': w3.eth.chain_id
        }
        log_message(f"Menandatangani transaksi ke: {final_tx['to']}...")
        signed_tx = w3.eth.account.sign_transaction(final_tx, account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        log_message(f"Transaksi terkirim. Hash: {tx_hash.hex()}")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=360)
        
        if tx_receipt.status == 1:
            log_message("-> Transaksi SUKSES.")
            return True
        else:
            log_message("-> Transaksi GAGAL.")
            return False
    except Exception as e:
        log_message(f"ERROR saat eksekusi transaksi: {e}")
        return False
def get_token_balance(w3, account, token_info):
    """Mendapatkan saldo token ERC20 dalam unit terkecilnya (wei)."""
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_info['address']), abi=config.ERC20_ABI)
    return token_contract.functions.balanceOf(account.address).call()
def approve_token(w3, account, token_address, spender_address, amount):
    """Menyetujui (approve) sejumlah token untuk dibelanjakan oleh router."""
    log_message(f"Memberikan approval untuk {spender_address}...")
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=config.ERC20_ABI)
    tx = token_contract.functions.approve(spender_address, amount).build_transaction({
        'from': account.address, 'nonce': w3.eth.get_transaction_count(account.address), 'gas': 100000,
        'maxFeePerGas': w3.to_wei('10', 'gwei'), 'maxPriorityFeePerGas': w3.to_wei('1', 'gwei')
    })
    return execute_transaction(w3, account, tx)
def trigger_emergency_rebalance(w3, account):
    """
    Mencari satu token yang memiliki saldo dan menukarnya ke ETH untuk isi ulang.
    Mengembalikan True jika berhasil, False jika gagal.
    """
    log_message("Mencari token untuk dijual kembali ke ETH...")
    eth_address = "0x0000000000000000000000000000000000000000"
    token_items = list(config.TOKEN_LIST.items())
    random.shuffle(token_items)
    for symbol, info in token_items:
        if symbol == 'WETH': continue
        
        balance = get_token_balance(w3, account, info)
        if balance > 0:
            amount_to_swap = int(balance * config.REBALANCE_PERCENTAGE)
            human_readable_balance = amount_to_swap / (10**info['decimals'])
            log_message(f"Ditemukan {symbol} dengan saldo. Mencoba menjual {human_readable_balance:.6f} {symbol} untuk isi ulang ETH.")
            
            quote = get_api_quote(w3, info['address'], eth_address, amount_to_swap, account.address)
            if quote:
                approval_ok = approve_token(w3, account, info['address'], quote['to'], amount_to_swap)
                if approval_ok:
                    log_message("Approval berhasil. Melanjutkan dengan swap pembalikan.")
                    time.sleep(20)
                    swap_ok = execute_transaction(w3, account, quote)
                    if swap_ok:
                        log_message("Isi ulang ETH berhasil.")
                        return True
            log_message(f"Gagal melakukan rebalance untuk {symbol}, mencoba token lain...")
    log_message("Tidak ada token yang bisa dijual untuk mengisi ulang ETH.")
    return False
def run_swap_cycle(w3, account):
    """
    Fungsi utama yang menjalankan siklus swap dengan logika pengisian ulang darurat.
    """
    swap_target = random.randint(config.MIN_SWAP_COUNT, config.MAX_SWAP_COUNT)
    log_message(f"Memulai SIKLUS SWAP, menargetkan {swap_target} transaksi.")
    for i in range(swap_target):
        log_message(f"--- Memproses Swap #{i+1}/{swap_target} ---")
        
        eth_balance = w3.eth.get_balance(account.address)
        if eth_balance < w3.to_wei(config.MIN_ETH_BALANCE_THRESHOLD, 'ether'):
            log_message(f"PERINGATAN: Saldo ETH ({w3.from_wei(eth_balance, 'ether')} ETH) rendah. Memicu isi ulang darurat...")
            
            refuel_success = trigger_emergency_rebalance(w3, account)
            
            if not refuel_success:
                log_message("KRITIS: Gagal mengisi ulang ETH. Tidak dapat melanjutkan siklus. Bot akan menunggu sebelum mencoba siklus baru.")
                break
            else:
                log_message("Isi ulang berhasil, melanjutkan siklus.")
        
        target_symbol = random.choice(list(config.TOKEN_LIST.keys()))
        amount_to_swap = random.uniform(config.MIN_ETH_AMOUNT, config.MAX_ETH_AMOUNT)
        amount_wei = w3.to_wei(amount_to_swap, 'ether')
        log_message(f"Eksekusi swap: {amount_to_swap:.8f} ETH ke {target_symbol}...")
        
        quote = get_api_quote(
            w3, "0x0000000000000000000000000000000000000000",
            config.TOKEN_LIST[target_symbol]['address'],
            amount_wei, account.address
        )
        if quote:
            execute_transaction(w3, account, quote)
        if i < swap_target - 1:
             delay = random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
             log_message(f"Jeda acak: Menunggu {delay/60:.2f} menit...")
             time.sleep(delay)
    log_message(f"Siklus {swap_target} swap telah selesai.")
def main():
    """Fungsi utama untuk menjalankan siklus bot tanpa henti."""
    log_message("="*40)
    log_message("   Memulai Auto SWAP")
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
