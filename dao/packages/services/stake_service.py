from .__init__ import Stake, Dao, logger, DaoConfirmationService


class StakeService:
    """helper class to isolate business logic for serializer"""

    @staticmethod
    def create_stake_instance(user, dao_id=None, slug=None):
        logger.info(f"passed id: {dao_id}, passed user: {user}")

        dao = Dao.objects.get(id=dao_id) if dao_id else Dao.objects.get(slug=slug)

        dao_contracts = dao.dao_contracts.first()

        staking_address = dao_contracts.staking_address
        blockchain_service = DaoConfirmationService(
            dao_address=dao_contracts.dao_address, network=dao.network
        )
        staked_amount = blockchain_service.read_staked_amount(
            staking_address=staking_address, user_address=user.eth_address
        )
        stake = Stake.objects.filter(user=user, dao=dao).first()

        if not stake:
            stake = Stake.objects.create(
                amount=staked_amount,
                user=user,
                dao=dao,
            )
        else:
            stake.amount = staked_amount
            stake.save()

        stake_dict = stake.__dict__

        stake_dict.pop("id", None)
        stake_dict.pop("user", None)
        stake_dict.pop("dao", None)
        return stake_dict

    @staticmethod
    def has_staked_amount(user, dao):
        stake = Stake.objects.filter(user=user, dao=dao).first()
        return stake and stake.amount > 0
