from pydantic import BaseModel, EmailStr
from typing import Optional,Literal
from enum import Enum
from app.models.user.user import UserRole

class UserRoleEnum(str, Enum):
    general = "general"
    provider = "provider"
 

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: Literal["general", "provider", "admin"] 


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: str

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str]=None
    email: Optional[EmailStr]=None
    password: Optional[str]=None

    
class ProviderProfileCreate(BaseModel):
    name: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    location: Optional[str]
    description: Optional[str]

class ProviderProfileResponse(BaseModel):
    id: int
    name: str
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    location: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


# Schema for incoming request
class ChooseRoleRequest(BaseModel):
    role:Literal["general", "provider", "admin"]