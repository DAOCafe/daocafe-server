from django.core.files.uploadedfile import SimpleUploadedFile


from core.helpers.create_user import create_user
from dao.models import Dao, Contract
from uuid import uuid4


class DaoBaseMixin:
    def __init__(self, owner=None):
        self.dao_image = SimpleUploadedFile(
            "some_image.png", b"image_file_indeed", content_type="image/png"
        )
        self.slug = "slugish"
        self.owner = owner or create_user()
        self.dao_name = f"dao_{uuid4().hex[:8]}"

        # ? NEEDS CONTRACTS PROPERTY ?

    def create_dao(self, **overrides):
        dao_data = {
            "owner": self.owner,
            "dao_name": self.dao_name,
            "dao_image": self.dao_image,
            "slug": self.slug,
            "description": "description",
            "cover_image": SimpleUploadedFile(
                "some_image1.png", b"image_file_indeed1", content_type="image/png"
            ),
            "socials": {"discord": "hello world", "telegram": "@username"},
            "is_active": True,
            "dip_count": 0,
            "network": "11155111",
            "token_name": "token",
            "symbol": "eth",
            "total_supply": 88888888888888888,
            "version": "1.0.0",
            # "contracts": "",
        }

        dao_data.update(**overrides)

        return Dao.objects.create(**dao_data)


class DaoFactoryMixin(DaoBaseMixin):
    def create_dao(self, **overrides):
        dao = super().create_dao(**overrides)

        Contract.objects.create(
            dao=dao,
            dao_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            token_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            treasury_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
            staking_address="0x" + uuid4().hex[:32] + uuid4().hex[:8],
        )
        return dao
