import time, os, json
from web3 import Web3
from logging_config import logger


class BlockchainClient:
    def __init__(
        self, dao_address: str = None, network: int = None, retries: int = 3
    ):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
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
        # Log the provider URL with redacted API key if present
        logged_url = provider_url
        if "api_key" in provider_url:
            provider_url = provider_url.format(
                api_key=os.environ.get("ANKR_PROJECT_ID")
            )
            logged_url = provider_url.split("api_key=")[0] + "api_key=***"
        
        logger.info(f"Attempting to connect to network {self.network} using provider: {logged_url}")
        
        if "api_key" in provider_url and not os.environ.get("ANKR_PROJECT_ID"):
            logger.error("ANKR_PROJECT_ID environment variable is not set")
            raise ConnectionError("ANKR_PROJECT_ID environment variable is required but not set")

        web3 = None
        for attempt in range(1, self.retries + 1):
            logger.info(f"Connection attempt {attempt}/{self.retries}")
            try:
                provider = Web3.HTTPProvider(provider_url)
                # Try to make an actual request to test the connection
                try:
                    response = provider.make_request("eth_blockNumber", [])
                    if "error" in response:
                        logger.warning(f"Connection attempt {attempt} failed: RPC error: {response['error']}")
                        raise ConnectionError(f"RPC error: {response['error']}")
                except Exception as rpc_error:
                    logger.warning(f"Connection attempt {attempt} failed with RPC error: {str(rpc_error)}")
                    raise

                web3 = Web3(provider)
                if web3.is_connected():
                    logger.info(f"Connection with chain {self.network} established successfully")
                    return web3
                else:
                    logger.warning(f"Connection attempt {attempt} failed: Web3 could not connect to RPC endpoint")
            except Exception as e:
                logger.warning(f"Connection attempt {attempt} failed with error details: {type(e).__name__}: {str(e)}")
            
            if attempt < self.retries:
                logger.info(f"Waiting {self.delay} seconds before next attempt...")
                time.sleep(self.delay)
        
        logger.error(f"Failed to connect to network {self.network} after {self.retries} attempts")
        raise ConnectionError(f"Could not connect to network {self.network} after {self.retries} attempts")

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
            1337: "http://host.docker.internal:8545",
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
