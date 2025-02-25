from forum.models import Dip
from dao.tests.dao_utils import DaoFactoryMixin, DaoBaseMixin
from datetime import datetime, timedelta


class DipBaseMixin:
    def __init__(self, dao=None, author=None):
        self.dao = dao
        self.author = author

    def create_dip(self):
        return Dip.objects.create(
            title="no title",
            content="no-content",
            dao=self.dao,
            author=self.author,
            status="active",
            end_time=int((datetime.utcnow() + timedelta(days=7)).timestamp()),
            proposal_id=1,
            proposal_type="transfer",
            proposal_data={"some data here": "ok"},
        )
