import time, os, json
from web3 import Web3
from logging_config import logger


class BlockchainClient:
    def __init__(
        self, dao_address: str = None, network: int = 11155111, retries: int = 3
    ):
        self.network = network
        self.retries = retries
        self.delay = 2
        self.dao_address = (
            Web3.to_checksum_address(dao_address) if dao_address else None
        )
        self.web3 = self.connect()
        self.current_block = self.web3.eth.block_number
        self.from_block = max(0, self.current_block - 100000)

    def connect(self):
        provider_url = self.get_provider(self.network)
        if "api_key" in provider_url:
            provider_url = provider_url.format(
                api_key=os.environ.get("ANKR_PROJECT_ID")
            )

        web3 = None
        for attempt in range(1, self.retries + 1):
            web3 = Web3(Web3.HTTPProvider(provider_url))
            if web3.is_connected():
                logger.info(f"connection with chain {self.network} established")
                return web3

            logger.warning(f"connection {attempt} failed")
            time.sleep(self.delay)
        logger.error(f"failed to connect to network {self.network}")
        raise ConnectionError(f"could not connect to network {self.network}")

    @staticmethod
    def get_provider(network):
        provider_urls = {
            1: "https://mainnet.infura.io/v3/{api_key}",
            5: "https://goerli.infura.io/v3/{api_key}",
            10: "https://optimism-mainnet.infura.io/v3/{api_key}",
            56: "https://bsc-dataseed.binance.org/",
            137: "https://polygon-mainnet.infura.io/v3/{api_key}",
            42161: "https://arbitrum-mainnet.infura.io/v3/{api_key}",
            11155111: "https://rpc.ankr.com/eth_sepolia/{api_key}",
        }

        if network not in provider_urls:
            raise ValueError(f"Unknown network: {network}")

        return provider_urls[network]

    @staticmethod
    def get_abi(abi_name):
        file_path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)), "ABIs.json"
        )
        try:
            with open(file_path, "r") as file:
                abi_data = json.load(file)
                return abi_data.get(abi_name)
        except FileNotFoundError:
            logger.error(f"abi file not found: {file_path}")
            raise
        except json.JSONDecodeError:
            logger.error(f"failed to parse abi json file: {file_path}")
            raise
