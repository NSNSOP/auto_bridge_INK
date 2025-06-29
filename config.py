WEB3_PROVIDER_URL = "https://rpc-qnd.inkonchain.com"
PRIVATE_KEY = "0xPrivatekeyHere"  # Replace with your actual private key
MIN_SWAP_COUNT = 15
MAX_SWAP_COUNT = 30
MIN_ETH_AMOUNT = 0.000001
MAX_ETH_AMOUNT = 0.000006
REBALANCE_PERCENTAGE = 0.90
MIN_ETH_BALANCE_THRESHOLD = 0.00005
MIN_DELAY_SECONDS = 8 * 60
MAX_DELAY_SECONDS = 15 * 60
TOKEN_LIST = {
    "USDT0": {"address": "0x0200C29006150606B650577BBE7B6248F58470c1", "decimals": 6},
    "USDC":  {"address": "0xf1815bd50389c46847f0bda824ec8da914045d14", "decimals": 6},
    "WETH":  {"address": "0x4200000000000000000000000000000000000006", "decimals": 18},
    "KBTC":  {"address": "0x73e0c0d45e048d25fc26fa3159b0aa04bfa4db98", "decimals": 8}
}
ERC20_ABI = """
[
    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
    {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}
]
"""