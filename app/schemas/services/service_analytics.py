from pydantic import BaseModel


class TotalServicesCountResponse(BaseModel):
    total_services: int
