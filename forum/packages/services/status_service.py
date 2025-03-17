from dao.models import Dao, Presale, PresaleStatus, Treasury
from forum.models import Dip, DipStatus, ProposalType
from services.blockchain.dip_service import DipConfirmationService
from services.blockchain.treasury_service import TreasuryService
from dao.packages.services.presale_service import PresaleService
from datetime import datetime
from django.shortcuts import get_object_or_404
from forum.tasks import sync_votes_task
from logging_config import logger
from web3 import Web3


class UpdateStatus:

    def fetch_contract(self, dip):
        """
        Fetch the contract for a given DIP
        
        Args:
            dip: The DIP object
            
        Returns:
            The contract object
        """
        dao = get_object_or_404(Dao, id=dip.dao_id)
        contract = dao.contracts.first()
        logger.info(f"dip:{dip}dao:{dao}contract:{contract}")
        if contract is None:
            raise ValueError("no contract was found")
        return contract

    def create_presale_instance(self, dip, contract, proposal_id):
        """
        Create a Presale instance for an executed presale proposal
        
        Args:
            dip: The DIP object
            contract: The contract object
            proposal_id: The proposal ID
            
        Returns:
            The created Presale instance or None if creation fails
        """
        try:
            # Check if an ACTIVE Presale instance already exists for this DAO
            existing_presale = Presale.objects.filter(
                dao_id=dip.dao_id,
                presale_contract__isnull=False,
                status=PresaleStatus.ACTIVE  # Only consider ACTIVE presales as existing
            ).first()
            
            if existing_presale:
                logger.info(f"Presale instance already exists for proposal {proposal_id}")
                return None
            
            # Get presale contract address from DAO contract
            dip_service = DipConfirmationService(dao_address=contract.dao_address, network=contract.network)
            dao_abi = dip_service.get_abi("dip_abi")
            web3 = dip_service.web3
            dao_contract = web3.eth.contract(address=Web3.to_checksum_address(contract.dao_address), abi=dao_abi)
            
            # Call getPresaleContract function
            presale_contract = dao_contract.functions.getPresaleContract(proposal_id).call()
            
            # Verify presale contract is not empty
            if not presale_contract or presale_contract == "0x0000000000000000000000000000000000000000":
                logger.error(f"Invalid presale contract address for proposal {proposal_id}")
                return None
            
            # Get presale data
            presale_data = dip_service.get_type(proposal_id, int(ProposalType.PRESALE), dao_contract)
            
            # Create Presale instance
            presale = Presale.objects.create(
                dao_id=dip.dao_id,
                presale_contract=presale_contract,
                total_token_amount=presale_data[1],  # amount
                initial_price=presale_data[2],  # initialPrice
                status=PresaleStatus.ACTIVE
            )
            
            # Update presale state by calling getPresaleState on the contract
            presale_service = PresaleService(
                presale_contract=presale_contract,
                network=contract.network
            )
            presale_service.update_presale_state(presale)
            
            logger.info(f"Created Presale instance for proposal {proposal_id}")
            return presale
            
        except Exception as ex:
            logger.error(f"Failed to create Presale instance: {str(ex)}")
            # Continue with status update even if presale creation fails
            return None

    def update_dip_status(self, dip):
        """
        Update the status of a DIP
        
        Args:
            dip: The DIP object to update
            
        Returns:
            The updated DIP object
        """
        contract = self.fetch_contract(dip)
        proposal_id = dip.proposal_id

        dip_service = DipConfirmationService(dao_address=contract.dao_address, network=contract.network)
        
        proposal = dip_service.get_proposals(proposal_id=proposal_id)
        if not proposal:
            raise ValueError("no proposal data found")

        proposal_end_time = datetime.fromtimestamp(proposal["end_time"])
        dip_end_time = datetime.fromtimestamp(dip.end_time)

        current_time = datetime.now()

        is_time_ended = (
            dip_end_time == proposal_end_time and proposal_end_time <= current_time
        )
        logger.info(f"is time ended: {is_time_ended}")
        logger.info(f"proposal: {proposal}")

        if is_time_ended:
            sync_votes_task(dip.id)
            status = self.convert_status(proposal["executed"])
            logger.info(f"status: {status}")
            logger.info(
                f"Votes for: {proposal.get('for_votes')}, votes against: {proposal.get('against_votes')}"
            )
            if (
                proposal.get("for_votes", 0) == 0
                and proposal.get("against_votes", 0) == 0
            ):
                dip.status = DipStatus.FAILED
            elif status is not None:
                # If the proposal is executed, update the treasury balance
                if status == DipStatus.EXECUTED:
                    # Update treasury balance for the DAO
                    self.update_treasury_balance(dip.dao)
                    
                    # If proposal is executed and it's a presale proposal, create Presale instance
                    if int(dip.proposal_type) == int(ProposalType.PRESALE):
                        self.create_presale_instance(dip, contract, proposal_id)
                    # If proposal is executed and it's a presale withdraw proposal, set presale status to COMPLETED
                    elif int(dip.proposal_type) == int(ProposalType.PRESALE_WITHDRAW):
                        # Get the presale contract address from the proposal data
                        presale_contract_address = None
                        if dip.proposal_data and "presale_contract" in dip.proposal_data:
                            presale_contract_address = dip.proposal_data["presale_contract"]
                        
                        if presale_contract_address:
                            # Find the presale instance with this contract address
                            presale = Presale.objects.filter(
                                dao_id=dip.dao_id,
                                presale_contract__iexact=presale_contract_address
                            ).first()
                            
                            if presale:
                                # Update status to COMPLETED
                                presale.status = PresaleStatus.COMPLETED
                                presale.save()
                                logger.info(f"Updated presale status to COMPLETED for presale {presale.id} with contract {presale_contract_address} after Presale Withdraw execution")
                            else:
                                logger.warning(f"No presale found with contract address {presale_contract_address} for DAO {dip.dao_id}")
                        else:
                            logger.warning(f"No presale contract address found in proposal data for DIP {dip.id}")
                
                dip.status = status

            dip.save()

        return dip

    def convert_status(self, executed_state):
        status_map = {
            True: DipStatus.EXECUTED,
        }
        return status_map.get(executed_state)
        
    def update_treasury_balance(self, dao):
        """Update the treasury balance for a DAO"""
        try:
            contract = dao.contracts.first()
            if not contract:
                logger.warning(f"No contract found for DAO {dao.id}")
                return
                
            treasury_service = TreasuryService(
                treasury_address=contract.treasury_address,
                network=contract.network
            )
            
            # Get balances
            ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
            token_balance = treasury_service.get_token_balance(contract.token_address)
            native_balance = treasury_service.get_native_balance()
            
            # Create or update treasury with balances
            treasury, created = Treasury.objects.update_or_create(
                dao=dao,
                defaults={
                    'balances': {
                        contract.token_address: str(token_balance),
                        ZERO_ADDRESS: str(native_balance)
                    }
                }
            )
            
            logger.info(f"Updated treasury balances for DAO {dao.id}: token={token_balance}, native={native_balance}")
            
        except Exception as ex:
            logger.error(f"Failed to update treasury balance: {str(ex)}")
