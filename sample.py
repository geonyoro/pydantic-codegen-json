from pydantic import BaseModel, Field


class BType(BaseModel):
    ba: str
    bb: str


class BType2(BaseModel):
    ba: str
    bc: str


class CType(BaseModel):
    ca: str
    cb: list[str]


class DType(BaseModel):
    da: str


class DType2(BaseModel):
    db: str


class RootType(BaseModel):
    a: str
    b: list[BType2 | BType | str]
    c: CType
    d: list[DType | DType2]
