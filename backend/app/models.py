from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class CreateStoreRequest(BaseModel):
    """Request model for creating a new store"""
    store_name: str = Field(..., min_length=3, max_length=20, pattern="^[a-z0-9-]+$", 
                             description="Store name (lowercase, alphanumeric, hyphens only)")
    owner_email: EmailStr = Field(..., description="Store owner email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "store_name": "my-awesome-store",
                "owner_email": "owner@example.com"
            }
        }


class StoreResponse(BaseModel):
    """Response model for store information"""
    store_name: str
    namespace: str
    url: str
    admin_url: str
    owner_email: Optional[str] = None
    status: str = "active"
    created_at: Optional[str] = None


class CreateStoreResponse(BaseModel):
    """Response model after creating a store"""
    status: str
    message: str
    data: dict


class StoreListResponse(BaseModel):
    """Response model for listing stores"""
    count: int
    stores: list[StoreResponse]


class DeleteStoreResponse(BaseModel):
    """Response model for deleting a store"""
    status: str
    message: str
    store_name: str


class HealthResponse(BaseModel):
    """Health check response"""
    healthy: bool
    kubernetes_connected: bool
    helm_installed: bool
