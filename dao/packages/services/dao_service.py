from .__init__ import transaction, Dao, Contract, logger, model_to_dict


class DaoService:
    """Handles DAO and contract creation"""

    @staticmethod
    def instanciate_dao_and_contracts(user, chain_data):
        """instanciates DAO and contract instances from chain data"""

        is_exist = Contract.objects.filter(
            dao_address=chain_data["dao_address"]
        ).first()

        is_exist_dao = Dao.objects.filter().first()

        if is_exist:
            logger.debug(f"is exist: {is_exist.__dict__}")
            return is_exist

        else:
            with transaction.atomic():
                dao = Dao.objects.create(
                    owner=user,
                    dao_name=chain_data["dao_name"],
                    token_name=chain_data["token_name"],
                    symbol=chain_data["symbol"],
                    total_supply=chain_data["total_supply"],
                    network=chain_data["network"],
                    version=chain_data["version"],
                )
                contracts = Contract.objects.create(
                    dao=dao,
                    dao_address=chain_data["dao_address"],
                    token_address=chain_data["token_address"],
                    treasury_address=chain_data["treasury_address"],
                    staking_address=chain_data["staking_address"],
                )
                if dao and contracts:
                    logger.info(
                        f"dao and contracts have been successfully instanciated"
                    )

            return contracts
