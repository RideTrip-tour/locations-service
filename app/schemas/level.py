from pydantic import BaseModel, ConfigDict, Field


class LevelBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class LevelCreate(LevelBase):
    pass


class LevelRead(LevelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
