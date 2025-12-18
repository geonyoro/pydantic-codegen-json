import json
import sys

OTHER_TYPES = []

BUFFER = []
PARTIAL_BUFFER = []

SEPARATOR = "    "

def bufwrite(*args, sep=" ", end="\n"):
    "Writes to the partial buffer."
    PARTIAL_BUFFER.append(sep.join(args) + end)


def bufcommit():
    BUFFER.append("".join(PARTIAL_BUFFER))
    PARTIAL_BUFFER.clear()


def generate(obj, key, with_commit: bool=True):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, list):
                bufwrite(SEPARATOR + key + ":", "list[", end="")
                generate(value, key, with_commit=False)
                bufwrite("]")
            elif isinstance(value, dict):
                type_name = key.title() + "Type"
                bufwrite(SEPARATOR + key + ":", type_name)
                OTHER_TYPES.append((type_name, value))
            else:
                generate(value, key)

    elif isinstance(obj, list):
        key_count = 1
        types = set()
        for val in obj:
            if isinstance(val, str):
                types.add("str")
            elif isinstance(val, int):
                types.add("int")
            elif isinstance(val, dict):
                new_type_name = f"{key.title()}Type"
                if key_count > 1:
                    new_type_name += str(key_count)
                key_count += 1
                types.add(new_type_name)
                OTHER_TYPES.append((new_type_name, val))
            else:
                raise ValueError(f"Unhandled {val=}")

        bufwrite(" | ".join(set(types)), end="")

    elif isinstance(obj, (str | int)):
        bufwrite(SEPARATOR + key + ":", type(obj).__name__, end="")

    if with_commit:
        bufcommit()

with open(sys.argv[1]) as wfile:
    data = json.load(wfile)

classname = "Data"
bufwrite("class %s(BaseModel):" % classname)
generate(data, classname)
bufwrite()
print("from pydantic import BaseModel\n")
MAIN_DS = "\n".join(BUFFER)
BUFFER.clear()
PARTIAL_BUFFER.clear()
for otype in OTHER_TYPES[-1::-1]:
    bufwrite("class %s(BaseModel):" % otype[0])
    generate(otype[1], otype[0])
    bufwrite()

# print("\n".join(BUFFER))
for i in BUFFER:
    print(i)

print("\n", MAIN_DS)
