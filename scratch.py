from uuid import uuid4

dao_address = "0x" + uuid4().hex[:32] + uuid4().hex[:8]
chars = uuid4().hex[:40]

print(len(dao_address))
