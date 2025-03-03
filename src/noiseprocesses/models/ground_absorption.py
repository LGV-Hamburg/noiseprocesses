from pydantic import BaseModel, Field

class GroundAbsorption(BaseModel):
    absorption: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Ground absorption coefficient"
    )
