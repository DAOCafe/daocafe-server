from .blockchain_client import BlockchainClient
from web3 import Web3
from logging_config import logger
from typing import Union


class DipConfirmationService(BlockchainClient):
    def __init__(
        self, dao_address: str = None, network: int = 11155111, retries: int = 3
    ):
        super().__init__(dao_address=dao_address, network=network, retries=retries)

    def get_proposal_count(self) -> tuple:
        if not self.dao_address:
            raise ValueError("no address was provided")
        dao_address = Web3.to_checksum_address(self.dao_address)
        abi = self.get_abi("dip_abi")
        contract = self.web3.eth.contract(address=dao_address, abi=abi)

        for attempt in range(self.retries):
            try:
                count = contract.functions.proposalCount().call()
                logger.info(f"count from blockchain: {count}")
                return count - 1, contract
            except Exception as ex:
                if attempt == self.retries - 1:
                    raise Exception(
                        f"failed to get proposal count after {self.retries} attempts"
                    ) from ex

    def get_proposals(self, excluded_proposals=None, proposal_id=None) -> dict | list:
        excluded_proposals = excluded_proposals or set()
        count, contract = self.get_proposal_count()
        if proposal_id is not None:
            proposal_data = contract.functions.getProposal(proposal_id).call()
            return {
                "proposal_id": proposal_id,
                "proposal_type": proposal_data[0],
                "for_votes": proposal_data[1],
                "against_votes": proposal_data[2],
                "end_time": proposal_data[3],
                "executed": proposal_data[4],
            }
        proposals = []
        for proposal_id in range(count, -1, -1):
            if proposal_id in excluded_proposals:
                continue
            proposal_data = contract.functions.getProposal(proposal_id).call()

            proposals.append(
                {
                    "proposal_id": proposal_id,
                    "proposal_type": proposal_data[0],
                    "for_votes": proposal_data[1],
                    "against_votes": proposal_data[2],
                    "end_time": proposal_data[3],
                    "executed": proposal_data[4],
                }
            )
        return proposals, contract

    def get_proposal_data(self, excluded_proposals=None) -> list:
        proposals, contract = self.get_proposals(excluded_proposals)
        complete_proposals = []

        for proposal in proposals:
            proposal_id = proposal["proposal_id"]
            proposal_type = proposal["proposal_type"]

            additional_data = self.get_type(
                proposal_id,
                proposal_type,
                contract,
            )

            complete_proposal = {
                **proposal,
                "token": additional_data[0],
                "recipient": additional_data[1],
                "amount": additional_data[2],
            }
            complete_proposals.append(complete_proposal)
        return complete_proposals

    def get_type(
        self, proposal_id: int, type_: int, contract
    ) -> Union[list, None, Exception]:
        if type_ not in range(0, 2):
            logger.error(f"invalid proposal type: {type_}")
            return None
        try:
            match type_:
                case 0:
                    return contract.functions.getTransferData(proposal_id).call()
                case 1:
                    return contract.functions.getUpgradeData(proposal_id).call()
        except Exception as ex:
            logger.error(f"error getting data for proposal {proposal_id}: {ex}")
            raise ex
