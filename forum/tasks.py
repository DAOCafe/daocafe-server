from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from logging_config import logger


@shared_task(bind=True)
def dip_cleanup(self):
    from .models import Dip, DipStatus

    logger.info(f" task {self.request.id}: DIP cleanup started")
    try:
        now = timezone.now()

        cutoff_time = now - timedelta(days=1)
        logger.info(f"searching for dips created before: {cutoff_time}")

        dips_count = Dip.objects.filter(
            status=DipStatus.DRAFT, created_at__lte=cutoff_time
        ).count()

        logger.info(f"found {dips_count} dips to delete")

        if dips_count > 0:
            deleted_count, details = Dip.objects.filter(
                status=DipStatus.DRAFT, created_at__lte=cutoff_time
            ).delete()
            logger.info(f"dip cleanup completed, deleted: {deleted_count}")
        else:
            logger.info(f"no dips found to delete")

        return (
            f"processes {dips_count} dips deleted {dips_count if dips_count > 0 else 0}"
        )

    except Exception as ex:
        logger.error(f"error in dip_cleanup task: {str(ex)}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=2,
    autoretry_for=(Exception,),
    name="blockchain.sync_proposals",
)
def sync_proposals_task(self, dao_id: int):
    help = "handles the entire dip sync process"

    from services.blockchain.dip_sync_service import DipSyncronizationService

    try:

        from dao.models import Dao, Contract

        dao = Dao.objects.get(id=dao_id)

        contract = Contract.objects.get(dao=dao)

        logger.debug(f"contract is here: {contract}\n type: {(type(contract))}")

        sync_service = DipSyncronizationService(contract)
        result = sync_service.process_blockchain_data(dao)
        logger.info(f"result: {result}")

        return {
            "status": "completed",
            "message": f"syncronized {len(result)} proposals",
            "data": [dip.id for dip in result],
        }
    except Exception as ex:
        logger.error(f"async task failed: {str(ex)}")
        raise self.retry(exc=ex)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=3,
    autoretry_for=(Exception,),
    name="blockchain.sync_votes",
)
def sync_votes_task(self, proposal_id):
    help = "handles votes syncronization process"
    from .services.vote_service import VoteService

    try:
        vote_service = VoteService()

        result = vote_service.create_vote_instance(proposal_id)

        return {
            "status": "completed",
            "message": f"syncronized {len(result)} votes",
            "data": [vote for vote in result],
        }

    except Exception as ex:
        logger.error(f"async task failed: {str(ex)}")
        raise self.retry(exc=ex)
