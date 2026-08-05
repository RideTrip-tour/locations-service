from pydantic import BaseModel, ConfigDict, Field


class StyleBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class StyleCreate(StyleBase):
    pass


class StyleRead(StyleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
