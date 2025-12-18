from pydantic import BaseModel


class BType(BaseModel):
    ba: str
    bb: str


class BType2(BaseModel):
    bc: str
    bd: str


class CType(BaseModel):
    ca: str
    cb: list[str]


class DType(BaseModel):
    da: str


class DType2(BaseModel):
    db: str


class Data(BaseModel):
    a: str
    b: list[BType2 | BType | str]
    c: CType
    d: list[DType | DType2]
