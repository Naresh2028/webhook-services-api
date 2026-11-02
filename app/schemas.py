from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from datetime import datetime
from typing import Optional 

class WebhookPayload(BaseModel):
    transaction_id:str = Field(min_length=1, max_length=70)
    source_account: str = Field(min_length=1,max_length=80)
    destination_account:str = Field(min_length=1, max_length=60)
    amount:float = Field(gt=0) # Must be greater than 0
    currency:str = Field(min_length=3, max_length=5, examples=["USD"])
    
    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, value:str) -> str:
        return value.upper() # 'int' -> 'INR'
    
class TransactionOut(BaseModel):
    
    model_config =  ConfigDict(from_attributes=True)
    
    transaction_id : str
    source_account: str
    destination_account:str
    amount:float
    currency:str
    created_at:datetime
    processed_at: Optional[datetime] = None
    
    @field_serializer("created_at", "processed_at")
    def format_time(self,value:Optional[datetime]) -> Optional[str] :
        return None if value is None else value.strftime("%Y-%m-%dT%H:%M:%SZ")