import logging

from uuid import UUID
from fastapi import APIRouter, HTTPException, status

from bharatrag.domain.collection import CollectionCreate, Collection
from bharatrag.services.repositories.collection_repository import CollectionRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["collections"])
repo = CollectionRepository()


@router.post("", response_model=Collection, status_code=status.HTTP_201_CREATED)
def create_collection(payload: CollectionCreate) -> Collection:
    logger.info("Collection creation requested", extra={"collection_name": payload.name})
    try:
        collection = repo.create(payload)
        logger.info(
            "Collection created successfully",
            extra={"collection_id": str(collection.id), "collection_name": payload.name},
        )
        return collection
    except Exception as e:
        logger.exception(
            "Collection creation failed",
            extra={"collection_name": payload.name, "error": str(e)},
        )
        raise


@router.get("/{collection_id}", response_model=Collection)
def get_collection(collection_id: UUID) -> Collection:
    logger.debug("Collection fetch requested", extra={"collection_id": str(collection_id)})
    result = repo.get(collection_id)
    if result is None:
        logger.warning("Collection not found", extra={"collection_id": str(collection_id)})
        raise HTTPException(status_code=404, detail="Collection not found")
    logger.debug("Collection fetched successfully", extra={"collection_id": str(collection_id)})
    return result


@router.get("", response_model=list[Collection])
def list_collections(limit: int = 50, offset: int = 0) -> list[Collection]:
    logger.debug("List collections requested", extra={"limit": limit, "offset": offset})
    try:
        collections = repo.list(limit=limit, offset=offset)
        logger.info(
            "Collections listed successfully",
            extra={"count": len(collections), "limit": limit, "offset": offset},
        )
        return collections
    except Exception as e:
        logger.exception("List collections failed", extra={"error": str(e)})
        raise
