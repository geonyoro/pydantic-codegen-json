import hashlib
import json
import sys
import typing

OTHER_TYPES = []

SEPARATOR = "    "


type_registry = {}
type_count_registry = {}
node_tree = []


class Pair:
    def __init__(self, one, two):
        self.one = one
        self.two = two

    def to_xml_tree(self):
        return f"({self.one}, {self.two.to_xml_tree()})"


class TreeNode:
    def __init__(self):
        self.children: "list[Raw | NList | NDict]" = []


class Raw(TreeNode):
    def __init__(self, key_name: str, type_name: str, ancestry: list[str]):
        super().__init__()
        self.key_name = key_name
        self.type_name = type_name
        self.ancestry = ancestry

    def to_xml_tree(self):
        return self.type_name

    def generate(self):
        pass

    def to_type_name(self) -> str:
        return self.type_name


class NDict(TreeNode):
    def __init__(self, key_name: str, definition: dict, ancestry: list[str]):
        super().__init__()
        self.key_name = key_name
        self.ancestry = ancestry
        self.definition = definition

        level = len(self.ancestry)
        if len(node_tree) <= level + 1:
            node_tree.append([])
        node_tree[level].append(self)

        self.define()
        self._class_name = None
        self._lines = None
        self._is_computed = False

    def define(self):
        self.slots: list[Pair] = []
        for k, v in self.definition.items():
            if v is None:
                val_obj = Raw(k, "None", ancestry=self.ancestry + [self.key_name])
                continue  # TODO :Consider removal
            elif isinstance(v, dict):
                val_obj = NDict(k, v, ancestry=self.ancestry + [self.key_name])
            elif isinstance(v, list):
                val_obj = NList(k, v, ancestry=self.ancestry + [self.key_name])
            else:
                assert isinstance(v, (int, str))
                val_obj = Raw(
                    k, type(v).__name__, ancestry=self.ancestry + [self.key_name]
                )
            self.children.append(val_obj)
            self.slots.append(Pair(k, val_obj))

    def to_xml_tree(self):
        out = [f"<{self.key_name}:NDict>"]
        for i in self.slots:
            out.append(i.to_xml_tree())
        out.append(f"</{self.key_name}>")
        return "\n".join(out)

    def to_type_name(self) -> str:
        return self.compute()[1]

    def generate(self):
        return self.compute()[0]

    def compute(self) -> tuple[None | str, str]:
        if not self._is_computed:
            self._lines, self._class_name = self._compute()
            self._is_computed = True

        assert self._class_name
        return self._lines, self._class_name

    def _compute(self) -> tuple[str | None, str]:
        body_lines = []
        for p in self.slots:
            field_alias = ""
            field_key = p.one
            if field_key.startswith("_"):
                field_key = p.one.lstrip("_")
                field_alias = f' = Field(alias="{p.one}")'
            line = "%s%s: %s%s" % (
                " " * 4,
                field_key,
                p.two.to_type_name(),
                field_alias,
            )
            body_lines.append(line)

        body_definition = "\n".join(body_lines)
        digest = hashlib.md5(body_definition.encode()).hexdigest()
        try:
            return None, type_registry[digest]
        except KeyError:
            pass

        class_name = self.key_name
        if class_name.startswith("_"):
            class_name = class_name.lstrip("_")
        class_name = class_name[0].title() + class_name[1:] + "Type"

        # handle counting
        count = type_count_registry.get(class_name, 1)
        type_count_registry[class_name] = count + 1
        if count > 1:
            class_name += str(count)

        type_registry[digest] = class_name
        lines = f"class {class_name}(BaseModel):\n" + body_definition
        return lines, class_name


class NList(TreeNode):
    def __init__(self, key_name: str, definition: list, ancestry: list[str]):
        super().__init__()
        self.key_name = key_name
        self.slots: list[NList | NDict | Raw] = []
        self.ancestry = ancestry
        self.definition = definition

        level = len(self.ancestry)
        if len(node_tree) <= level + 1:
            node_tree.append([])
        node_tree[level].append(self)

        self.define()

    def define(self):
        for v in self.definition:
            if isinstance(v, dict):
                val_obj = NDict(
                    self.key_name, v, ancestry=self.ancestry + [self.key_name]
                )
            elif isinstance(v, list):
                val_obj = NList(
                    self.key_name, v, ancestry=self.ancestry + [self.key_name]
                )
            else:
                assert isinstance(v, (int, str))
                val_obj = Raw(
                    self.key_name,
                    type(v).__name__,
                    ancestry=self.ancestry + [self.key_name],
                )
            self.children.append(val_obj)
            self.slots.append(val_obj)

    def to_xml_tree(self):
        elems = [i.to_xml_tree() for i in self.slots]
        out = "\n".join(elems)
        return f"NList:[{out}]"

    def to_type_name(self):
        types = sorted(list(set(i.to_type_name() for i in self.slots)))
        type_union_str = " | ".join(types)
        return "list[%s]" % type_union_str

    def generate(self):
        pass


Node = Raw | NDict | NList


def combine_nodes(nodes_to_combine: list[NDict]):
    count = len(nodes_to_combine)
    if count <= 1:
        return

    for n in nodes_to_combine:
        print(n.generate())

    res = input(f"\nCombine these {count} classes?[Y/n]").strip()
    if res and res.lower() not in ("y", "yes"):
        return

    lines = []
    classdef = ""
    base_node = None
    # make some optional
    for idx, n in enumerate(nodes_to_combine):
        out = n.generate()
        assert out
        out_parts = out.split("\n")
        lines.extend(out_parts[1:])
        if idx == 0:
            base_node = n
            classdef = out_parts[0]
        else:
            n._lines = []
            n._class_name = base_node._class_name

    # lines without class def
    lines = "\n".join([classdef] + lines)
    assert base_node
    base_node._lines = lines


def handle_data(data):
    if isinstance(data, list):
        NList("Root", data, ancestry=[])
    elif isinstance(data, dict):
        NDict("Root", data, ancestry=[])
    else:
        Raw("Root", data, ancestry=[])


def node_name_sort(name):
    """Converts name to have digits"""
    if name.startswith("list["):
        return name

    digits = ""
    break_idx = len(name)
    for idx in range(len(name) - 1, -1, -1):
        # check
        chr = name[idx]
        if chr not in "0123456789":
            break
        break_idx = idx
        digits = chr + digits

    digit_count = len(str(max_type_count))
    for _ in range(len(digits), digit_count):
        digits = "0" + digits

    final_name = name[:break_idx] + digits
    return final_name


with open(sys.argv[1]) as wfile:
    handle_data(json.load(wfile))


# TODO: Handle determining imports better
print("from pydantic import BaseModel, Field\n\n")


max_type_count = 0
for idx in range(len(node_tree) - 1, -1, -1):
    nodes_at_level = node_tree[idx]

    names_to_level_nodes: dict[str, list[TreeNode]] = {}
    combination_nodes: dict[str, list[Node]] = {}
    for n in nodes_at_level:
        tname = n.to_type_name()
        if tname not in names_to_level_nodes:
            names_to_level_nodes[tname] = []
        names_to_level_nodes[tname].append(n)

        ancestry_str = ",".join(n.ancestry)
        comb_key = f"{ancestry_str}:{n.key_name}"
        if comb_key not in combination_nodes:
            combination_nodes[comb_key] = []
        combination_nodes[comb_key].append(n)

    found = False
    for key_name, node_group in combination_nodes.items():
        if len(node_group) <= 1:
            continue
        print_count = 0
        nodes_to_combine = []
        for n in node_group:
            ...
            generated = n.generate()
            if generated:
                nodes_to_combine.append(n)
        found = len(nodes_to_combine) > 1
        combine_nodes(nodes_to_combine)
        break

    # if found:
    #     break

    if type_count_registry.values():
        max_type_count = max(type_count_registry.values())

    for name in sorted(names_to_level_nodes.keys(), key=node_name_sort):
        for node in names_to_level_nodes[name]:
            generated = node.generate()
            if generated:
                print(generated)
                print()
