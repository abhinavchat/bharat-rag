from uuid import UUID
from fastapi import APIRouter, HTTPException, status

from bharatrag.domain.collection import CollectionCreate, Collection
from bharatrag.services.repositories.collection_repository import CollectionRepository

router = APIRouter(prefix="/collections", tags=["collections"])
repo = CollectionRepository()


@router.post("", response_model=Collection, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate) -> Collection:
    return repo.create(payload)


@router.get("/{collection_id}", response_model=Collection)
def get_collection(collection_id: UUID) -> Collection:
    result = repo.get(collection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return result


@router.get("", response_model=list[Collection])
def list_collections(limit: int = 50, offset: int = 0) -> list[Collection]:
    return repo.list(limit=limit, offset=offset)
