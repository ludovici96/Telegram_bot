from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from .base_model import BaseModel
import re
import logging

logger = logging.getLogger(__name__)

class GroupModel(BaseModel):
    def __init__(self, collection):
        """Initialize with MongoDB collection"""
        super().__init__(collection)
        # Ensure indexes for group operations
        self.collection.create_index('group_name', unique=True)
        self.collection.create_index('members')

    def validate_group_name(self, group_name: str) -> Tuple[bool, str]:
        """
        Validate group name format.
        Returns (is_valid, error_message)
        """
        if not group_name:
            return False, "Group name cannot be empty"
        
        if not re.match(r'^[a-zA-Z0-9_]{3,32}$', group_name):
            return False, "Group name must be 3-32 characters long and contain only letters, numbers, and underscores"
            
        return True, ""

    async def create_group(self, group_name: str, creator_id: int) -> Tuple[bool, str]:
        """
        Create a new group.
        Returns (success, message)
        """
        try:
            is_valid, error_msg = self.validate_group_name(group_name)
            if not is_valid:
                return False, error_msg

            # Check if group already exists
            existing_group = self.collection.find_one({'group_name': group_name})
            if existing_group:
                return False, "Group already exists"

            group_doc = {
                'group_name': group_name,
                'members': [creator_id],
                'created_by': creator_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            self.collection.insert_one(group_doc)
            return True, f"Group '{group_name}' created successfully"
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False, f"Error creating group: {str(e)}"

    async def add_member(self, group_name: str, user_id: int) -> Tuple[bool, str]:
        """
        Add a member to a group.
        Returns (success, message)
        """
        try:
            # Find the group
            group = self.collection.find_one({'group_name': group_name})
            if not group:
                # Try to create the group if it doesn't exist
                success, msg = await self.create_group(group_name, user_id)
                if not success:
                    return False, msg
                return True, f"Created new group '{group_name}' and joined"

            # Check if user is already a member
            if user_id in group['members']:
                return False, f"You are already a member of '{group_name}'"

            # Add member and update timestamp
            self.collection.update_one(
                {'group_name': group_name},
                {
                    '$push': {'members': user_id},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            
            return True, f"Successfully joined '{group_name}'"
            
        except Exception as e:
            logger.error(f"Error adding member: {e}")
            return False, f"Error joining group: {str(e)}"

    async def remove_member(self, group_name: str, user_id: int) -> Tuple[bool, str]:
        """
        Remove a member from a group.
        Returns (success, message)
        """
        try:
            # Find the group
            group = self.collection.find_one({'group_name': group_name})
            if not group:
                return False, f"Group '{group_name}' does not exist"

            # Check if user is a member
            if user_id not in group['members']:
                return False, f"You are not a member of '{group_name}'"

            # Remove member
            self.collection.update_one(
                {'group_name': group_name},
                {
                    '$pull': {'members': user_id},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )

            # Check if group is empty after removal
            updated_group = self.collection.find_one({'group_name': group_name})
            if not updated_group['members']:
                # Delete empty group
                self.collection.delete_one({'group_name': group_name})
                return True, f"Left '{group_name}'. Group was deleted as it has no members"

            return True, f"Successfully left '{group_name}'"
            
        except Exception as e:
            logger.error(f"Error removing member: {e}")
            return False, f"Error leaving group: {str(e)}"

    async def delete_group(self, group_name: str) -> Tuple[bool, str]:
        """
        Delete a group entirely.
        Returns (success, message)
        """
        try:
            # Find and validate group exists
            group = self.collection.find_one({'group_name': group_name.lower()})
            if not group:
                return False, f"Group '{group_name}' does not exist"

            # Delete the group
            result = self.collection.delete_one({'group_name': group_name.lower()})
            if result.deleted_count > 0:
                return True, f"Group '{group_name}' has been deleted"
            return False, "Failed to delete group"

        except Exception as e:
            logger.error(f"Error deleting group: {e}")
            return False, f"Error deleting group: {str(e)}"

    def get_group_members(self, group_name: str) -> Optional[List[int]]:
        """Get all members of a group"""
        try:
            group = self.collection.find_one({'group_name': group_name})
            return group['members'] if group else None
        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            return None

    def get_user_groups(self, user_id: int) -> List[str]:
        """Get all groups a user is member of"""
        try:
            groups = self.collection.find(
                {'members': user_id},
                {'group_name': 1}
            )
            return [group['group_name'] for group in groups]
        except Exception as e:
            logger.error(f"Error getting user groups: {e}")
            return []

    def get_group_info(self, group_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a group"""
        try:
            return self.collection.find_one({'group_name': group_name.lower()})
        except Exception as e:
            logger.error(f"Error getting group info: {e}")
            return None
