from typing import Self
from pydantic import BaseModel, Field


class GroundAbsorptionInternal(BaseModel):
    G: float = Field(
        alias="absorption",
        default=0.0, ge=0.0, le=1.0,
        description="Ground absorption coefficient"
    )

    @classmethod
    def from_user_model(cls, user_model: 'GroundAbsorption') -> Self:
        """Convert from user model to internal model."""
        # Pydantic v2 model_dump() with by_alias=True converts to internal field names
        return cls(**user_model.model_dump())

class GroundAbsorption(BaseModel):
    absorption: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Ground absorption coefficient"
    )

    def to_internal(self) -> GroundAbsorptionInternal:
        """Convert to internal model."""
        return GroundAbsorptionInternal.from_user_model(self)