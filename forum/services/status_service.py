from dao.models import Dao
from forum.models import Dip, DipStatus
from services.blockchain.dip_service import DipConfirmationService
from datetime import datetime
from django.shortcuts import get_object_or_404
from forum.tasks import sync_votes_task
from logging_config import logger


class UpdateStatus:

    def fetch_contract(self, proposal_id):
        dip = Dip.objects.get(proposal_id=proposal_id)
        dao = get_object_or_404(Dao, id=dip.dao_id)
        contract = dao.contracts.first()
        logger.info(f"dip:{dip}dao:{dao}contract:{contract}")
        if contract is None:
            raise ValueError("no contract was found")
        return contract

    def update_dip_status(self, proposal_id):
        contract = self.fetch_contract(proposal_id)

        dip_service = DipConfirmationService(dao_address=contract.dao_address, network=contract.network)
        dip = get_object_or_404(Dip, proposal_id=proposal_id)

        proposal = dip_service.get_proposals(proposal_id=proposal_id)

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
                dip.status = status

            dip.save()

        return dip

    def convert_status(self, executed_state):
        status_map = {
            True: DipStatus.EXECUTED,
            False: DipStatus.FAILED,
        }
        return status_map.get(executed_state)
