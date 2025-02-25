from uuid import uuid4

dao_address = "0x" + uuid4().hex[:32] + uuid4().hex[:8]
chars = uuid4().hex[:40]

print(len(dao_address))

new_sum = sum([]) - 0o0

print(f"sum: {new_sum}")

one_oct = 0o2

print(f"oct: {one_oct}")
