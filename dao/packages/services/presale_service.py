from web3 import Web3
from logging_config import logger
from dao.models import Presale, PresaleStatus
from services.blockchain.blockchain_client import BlockchainClient


class PresaleService(BlockchainClient):
    """
    Service for interacting with presale contracts and updating presale state
    """
    
    def __init__(self, presale_contract=None, network=None, retries=3):
        # If network is not provided, default to 11155111 (Sepolia)
        network = network if network is not None else 11155111
        super().__init__(dao_address=None, network=network, retries=retries)
        self.presale_contract = presale_contract
    
    def update_presale_state(self, presale_instance):
        """
        Update the presale state by calling getPresaleState on the presale contract
        
        Args:
            presale_instance: The Presale model instance to update
            
        Returns:
            The updated Presale instance or None if update fails
        """
        try:
            if not presale_instance.presale_contract:
                logger.error(f"No presale contract address for presale {presale_instance.id}")
                return None
            
            # Get contract ABI
            presale_abi = self.get_abi("presale_abi")
            
            # Create contract instance
            contract_address = Web3.to_checksum_address(presale_instance.presale_contract)
            contract = self.web3.eth.contract(address=contract_address, abi=presale_abi)
            
            # Call getPresaleState function
            state = contract.functions.getPresaleState().call()
            
            # Update presale instance with state data
            presale_instance.current_tier = state[0]
            presale_instance.current_price = state[1]
            presale_instance.remaining_in_tier = state[2]
            presale_instance.total_remaining = state[3]
            presale_instance.total_raised = state[4]
            
            # Update status based on total_remaining
            if int(presale_instance.total_remaining) == 0:
                presale_instance.status = PresaleStatus.COMPLETED
            
            # Save the updated instance
            presale_instance.save()
            
            logger.info(f"Updated presale state for presale {presale_instance.id}")
            return presale_instance
            
        except Exception as ex:
            logger.error(f"Failed to update presale state: {str(ex)}")
            return None
