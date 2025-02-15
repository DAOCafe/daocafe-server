ANKR_PROJECT_ID = "24d97fec20bba5a14eb31e57afeec01a17e41ae483422d027a59ade36f2c88bc"

from web3 import Web3

provider_url = "https://rpc.ankr.com/eth_sepolia/24d97fec20bba5a14eb31e57afeec01a17e41ae483422d027a59ade36f2c88bc"


web3 = Web3(Web3.HTTPProvider(provider_url))
assert not web3.is_connected(), "connected"
