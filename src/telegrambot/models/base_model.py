
from typing import Any, Dict, List, Optional
from pymongo import MongoClient
from pymongo.collection import Collection

class BaseModel:
    def __init__(self, collection: Collection):
        self.collection = collection

    def insert_one(self, document: Dict[str, Any]) -> str:
        result = self.collection.insert_one(document)
        return str(result.inserted_id)

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.collection.find_one(query)

    def find_many(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return list(self.collection.find(query))

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> bool:
        result = self.collection.update_one(query, {"$set": update})
        return result.modified_count > 0

    def delete_one(self, query: Dict[str, Any]) -> bool:
        result = self.collection.delete_one(query)
        return result.deleted_count > 0