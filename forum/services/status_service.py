from dao.models import Dao, Presale, PresaleStatus
from forum.models import Dip, DipStatus, ProposalType
from services.blockchain.dip_service import DipConfirmationService
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
            # Check if a Presale instance already exists for this proposal
            existing_presale = Presale.objects.filter(
                dao_id=dip.dao_id,
                presale_contract__isnull=False
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
                # If proposal is executed and it's a presale proposal, create Presale instance
                if status == DipStatus.EXECUTED and int(dip.proposal_type) == int(ProposalType.PRESALE):
                    self.create_presale_instance(dip, contract, proposal_id)
                
                dip.status = status

            dip.save()

        return dip

    def convert_status(self, executed_state):
        status_map = {
            True: DipStatus.EXECUTED,
            False: DipStatus.FAILED,
        }
        return status_map.get(executed_state)
