import hashlib
import json
import sys

OTHER_TYPES = []

SEPARATOR = "    "


class Def:
    def __init__(self, name: str):
        self.name = name
        self.lines: list[str] = []

    def hash(self) -> str:
        content = "\n".join(self.lines)
        hasher = hashlib.md5()
        # print("---content---")
        # print(content)
        # print("---content---")
        hasher.update(content.encode())
        return hasher.hexdigest()

    def append(self, val: str):
        self.lines.append(val)

    def print(self):
        print(f"class {self.name}(BaseModel):")
        print(SEPARATOR + f"\n{SEPARATOR}".join(self.lines))
        print("\n")


_generated_types = {}


def generate(obj, key, d: Def):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, list):
                types_def = generate(value, key, d)
                d.append(key + ": list[%s]" % types_def)
            elif isinstance(value, dict):
                type_name = key.title() + "Type"
                new_dict_d = Def(type_name)
                generate(value, key, new_dict_d)
                hash = new_dict_d.hash()
                if hash in _generated_types:
                    new_type_name = _generated_types[hash]
                    d.append(key + ": %s" % new_type_name)
                    continue
                _generated_types[hash] = type_name
                new_dict_d.print()
                d.append(key + ": %s" % type_name)
            else:
                generate(value, key, d=d)

    elif isinstance(obj, list):
        dict_key_count = 1
        types = set()
        for val in obj:
            if isinstance(val, str):
                types.add("str")
            elif isinstance(val, int):
                types.add("int")
            elif isinstance(val, dict):
                type_name = f"{key.title()}Type"
                if dict_key_count > 1:
                    type_name += str(dict_key_count)
                new_dict_d = Def(type_name)
                generate(val, key, new_dict_d)
                hash = new_dict_d.hash()
                if hash in _generated_types:
                    new_type_name = _generated_types[hash]
                    types.add(type_name)
                    continue
                _generated_types[hash] = type_name
                new_dict_d.print()
                dict_key_count += 1
                types.add(type_name)
            else:
                raise ValueError(f"Unhandled {val=}")

        return " | ".join(sorted(types))

    elif isinstance(obj, (str | int)):
        d.append(key + ": %s" % type(obj).__name__)


with open(sys.argv[1]) as wfile:
    data = json.load(wfile)

classname = "Data"
print("from pydantic import BaseModel\n\n")
d = Def(classname)
generate(data, classname, d)
d.print()
