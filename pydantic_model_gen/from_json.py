import hashlib
import json
import sys

OTHER_TYPES = []

SEPARATOR = "    "


type_registry = {}
type_count_registry = {}


class Pair:
    def __init__(self, one, two):
        self.one = one
        self.two = two

    def to_xml_tree(self):
        return f"({self.one}, {self.two.to_xml_tree()})"


class Raw:
    def __init__(self, key_name: str, type_name: str, ancestry: list[str]):
        self.key_name = key_name
        self.type_name = type_name
        self.ancestry = ancestry

    def to_xml_tree(self):
        return self.type_name

    def generate(self):
        pass

    def to_type_name(self) -> str:
        return self.type_name


class NDict:
    def __init__(self, key_name: str, definition: dict, ancestry: list[str]):
        self.key_name = key_name
        self.ancestry = ancestry
        self.definition = definition
        self.define()

    def define(self):
        self.slots: list[Pair] = []
        for k, v in self.definition.items():
            if v is None:
                obj_type = Raw(k, "None", ancestry=self.ancestry + [self.key_name])
            elif isinstance(v, dict):
                obj_type = NDict(k, v, ancestry=self.ancestry + [self.key_name])
            elif isinstance(v, list):
                obj_type = NList(k, v, ancestry=self.ancestry + [self.key_name])
            else:
                assert isinstance(v, (int, str))
                obj_type = Raw(
                    k, type(v).__name__, ancestry=self.ancestry + [self.key_name]
                )
            self.slots.append(Pair(k, obj_type))
        nodes.append(self)

    def to_xml_tree(self):
        out = [f"<{self.key_name}:NDict>"]
        for i in self.slots:
            out.append(i.to_xml_tree())
        out.append(f"</{self.key_name}>")
        return "\n".join(out)

    @property
    def name(self):
        return self.key_name

    def to_type_name(self):
        lines, type_name = self.compute()
        if not lines:
            # we found this in a digest
            return type_name

        key = self.key_name
        return key[0].title() + key[1:] + "Type"

    def generate(self):
        return self.compute()[0]

    def compute(self):
        body_lines = []
        for p in self.slots:
            field_alias = ""
            field_key = p.one
            if field_key.startswith("_"):
                field_key = p.one.lstrip("_")
                field_alias = f' = Field(alias="{p.one}")'
            line = "\t%s: %s%s" % (field_key, p.two.to_type_name(), field_alias)
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
        count = type_count_registry.get(class_name, 0)
        type_count_registry[class_name] = count + 1
        if count > 0:
            class_name += str(count)

        type_registry[digest] = class_name
        lines = f"class {class_name}:\n" + body_definition
        return lines, class_name


class NList:
    def __init__(self, key_name: str, definition: list, ancestry: list[str]):
        self.key_name = key_name
        self.slots: list[NList | NDict | Raw] = []
        self.ancestry = ancestry
        self.definition = definition
        self.define()

    def define(self):
        for v in self.definition:
            if isinstance(v, dict):
                obj_type = NDict(
                    self.key_name, v, ancestry=self.ancestry + [self.key_name]
                )
            elif isinstance(v, list):
                obj_type = NList(
                    self.key_name, v, ancestry=self.ancestry + [self.key_name]
                )
            else:
                assert isinstance(v, (int, str))
                obj_type = Raw(
                    self.key_name,
                    type(v).__name__,
                    ancestry=self.ancestry + [self.key_name],
                )
            self.slots.append(obj_type)
        nodes.append(self)

    def to_xml_tree(self):
        elems = [i.to_xml_tree() for i in self.slots]
        out = "\n".join(elems)
        return f"NList:[{out}]"

    def to_type_name(self):
        types = [i.to_type_name() for i in self.slots]
        type_union_str = " | ".join(types)
        return "list[%s]" % type_union_str

    def generate(self):
        pass


class NodeTree:
    nodes: list[NDict | NList | Raw] = []

    def append(self, node):
        self.nodes.append(node)

    def to_xml_tree(self):
        out = ["<Tree>"]
        for elem in self.nodes:
            out.append(elem.to_xml_tree())
        out.append("</Tree>")
        return "\n".join(out)


nodes = NodeTree()


def handle_data(data):
    if isinstance(data, list):
        nodes.append(NList("Root", data, ancestry=[]))
    elif isinstance(data, dict):
        nodes.append(NDict("Root", data, ancestry=[]))
    else:
        nodes.append(Raw("Root", data, ancestry=[]))


with open(sys.argv[1]) as wfile:
    handle_data(json.load(wfile))

for i in nodes.nodes:
    generated = i.generate()
    if not generated:
        continue
    print(generated)
    print()
