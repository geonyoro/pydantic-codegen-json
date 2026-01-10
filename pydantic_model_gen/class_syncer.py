import re
import sys


class ClassDef:
    def __init__(self, name: str, class_duplicate_id: int):
        self.keys = []
        self.kvs: list[list[str]] = []
        self.dup_id = class_duplicate_id
        self.class_name = name
        self.lines = []

    def add_line(self, line):
        line = line.strip()
        if not line:
            return
        if line.startswith("class "):
            self.class_name = line
            return
        left, right = line.split(":")
        left = left.strip()
        right = right.strip()
        self.kvs.append([left, right])
        self.keys.append(left)

    def update_from_other(self, other: "ClassDef"):
        # see what we have in other that we don't have here and update
        base_idx = 0
        other_idx = 0
        while True:
            try:
                base_k = self.kvs[base_idx]
            except IndexError:
                # bring everything else from other into here
                while True:
                    try:
                        other_k = other.kvs[other_idx]
                    except IndexError:
                        break
                    other_k[1] = join_w_none_type(other_k[1])
                    self.kvs.append(other_k)
                    other_idx += 1

                break

            try:
                other_k = other.kvs[other_idx]
            except IndexError:
                # take everything left and make it optional
                while True:
                    try:
                        base_k = self.kvs[base_idx]
                    except IndexError:
                        break
                    base_k[1] = join_w_none_type(base_k[1])
                    self.kvs[base_idx] = base_k
                    base_idx += 1
                break

            if base_k == other_k:
                # keep moving together
                base_idx += 1
                other_idx += 1
            elif base_k[0] == other_k[0]:
                # the keys are found in each other but are not the same values
                # concatenate them
                base_k[1] = join_types(base_k[1], other_k[1])
                self.kvs[base_idx] = base_k
                # keep moving together
                base_idx += 1
                other_idx += 1
            elif base_k[0] < other_k[0]:
                # the key in base is not found in other, make it optional here
                base_k[1] = join_w_none_type(base_k[1])
                self.kvs[base_idx] = base_k
                base_idx += 1
            else:
                # the key in other is not found in base, make it optional in other
                other_k[1] = join_w_none_type(other_k[1])
                self.kvs.insert(base_idx, other_k)
                other_idx += 1

    def print(self):
        print(f"class {self.class_name}(BaseModel):" + "\n", end="")
        for k, v in self.kvs:
            print(" " * 4 + f"{k}: {v}\n", end="")


def join_types(base_types_str: str, other_types_str: str) -> str:
    equality_rh = None
    try:
        equality_rh = base_types_str.split("=")[1].strip()
    except IndexError:
        pass

    try:
        equality_rh = other_types_str.split("=")[1].strip()
    except IndexError:
        pass

    base_types_str = base_types_str.replace(" = None", "")
    other_types_str = other_types_str.replace(" = None", "")
    base_types = set([i.strip() for i in base_types_str.split("|")])
    for otype in [i.strip() for i in other_types_str.split("|")]:
        base_types.add(otype)

    # if "FbaFeesType" in base_types_str:
    #     print()
    #     print(" BASE:", base_types_str)
    #     print("OTHER:", other_types_str)
    #     print("Equality:", equality_rh, type(equality_rh))
    #     print()

    ret_str = " | ".join(sorted(base_types, key=lambda x: x == "None"))
    if equality_rh:
        ret_str += f" = {equality_rh}"
    return ret_str


def join_w_none_type(base_types_str: str) -> str:
    final = join_types(base_types_str, "None")
    none_default = " = None"
    if none_default not in final:
        final += none_default

    return final


# sync_root_types
def sync_root_types():
    prev_name = None
    name_defs_map: dict[str, list[ClassDef]] = {}
    with open(sys.argv[1]) as wfile:
        for line in wfile.readlines():
            line = line.strip()

            if sobj := re.search(
                r"class (?P<name>\w+[a-zA-z])(?P<id>\d+)\(BaseModel\):", line
            ):
                # the above regex isn't greedy enough. When given Product29(BaseModel)
                # it spits out name:Product2 and id:9
                class_name = sobj["name"]
                count: int | None = int(sobj["id"])
            elif sobj := re.search(r"class (?P<name>\w+)", line):
                class_name = sobj["name"]
                count = 1
            else:
                class_name = count = None

            if class_name is not None and count is not None:
                if class_name != prev_name:
                    prev_name = class_name

                defs: list[ClassDef] = name_defs_map.get(class_name, [])
                current_cdef: ClassDef = ClassDef(class_name, count)
                defs.append(current_cdef)
                name_defs_map[class_name] = defs
                continue

            current_cdef = None
            if not prev_name:
                continue
            defs = name_defs_map.get(prev_name, [])
            if len(defs) > 0:
                current_cdef = defs[-1]

            current_cdef: ClassDef | None

            if not current_cdef:
                continue
            current_cdef.add_line(line)

    for defs in name_defs_map.values():
        base: ClassDef | None = None
        for cdef in defs:
            if base is None:
                base = cdef
                continue
            other = cdef
            base.update_from_other(other)
        assert base
        base.print()
        print()


sync_root_types()
