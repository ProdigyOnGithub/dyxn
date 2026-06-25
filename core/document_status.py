import time

from core.redis import redis_client


DOCUMENT_STATUS_TTL_SECONDS = 7 * 24 * 60 * 60
PROCESSING_STATUSES = {"queued", "chunking", "chunked", "embedding"}


def _status_key(owner_id, document_id):
    return f"document_status:{owner_id}:{document_id}"


def _owner_index_key(owner_id):
    return f"document_status_index:{owner_id}"


def _clean_mapping(mapping):
    cleaned = {}
    for key, value in mapping.items():
        if value is None:
            continue
        cleaned[key] = str(value)
    return cleaned


def update_document_status(owner_id, document_id, **fields):
    if owner_id is None or not document_id:
        return {}

    now = time.time()
    key = _status_key(owner_id, document_id)
    index_key = _owner_index_key(owner_id)
    mapping = _clean_mapping(
        {
            "owner_id": owner_id,
            "document_id": document_id,
            "updated_at": now,
            **fields,
        }
    )

    redis_client.hset(key, mapping=mapping)
    redis_client.expire(key, DOCUMENT_STATUS_TTL_SECONDS)
    redis_client.zadd(index_key, {document_id: now})
    redis_client.expire(index_key, DOCUMENT_STATUS_TTL_SECONDS)
    return get_document_status(owner_id, document_id)


def create_document_status(owner_id, document_id, filename, source_type):
    now = time.time()
    return update_document_status(
        owner_id,
        document_id,
        filename=filename,
        source_type=source_type,
        status="queued",
        created_at=now,
        total_chunks=0,
        embedded_chunks=0,
        error="",
    )


def mark_document_failed(owner_id, document_id, error):
    return update_document_status(
        owner_id,
        document_id,
        status="failed",
        error=str(error)[:1000],
    )


def mark_chunk_embedded(owner_id, document_id):
    if owner_id is None or not document_id:
        return {}

    key = _status_key(owner_id, document_id)
    embedded_chunks = redis_client.hincrby(key, "embedded_chunks", 1)
    status = get_document_status(owner_id, document_id)
    total_chunks = int(status.get("total_chunks") or 0)

    if total_chunks and embedded_chunks >= total_chunks:
        return update_document_status(
            owner_id,
            document_id,
            status="ready",
            embedded_chunks=embedded_chunks,
        )

    return update_document_status(
        owner_id,
        document_id,
        status="embedding",
        embedded_chunks=embedded_chunks,
    )


def get_document_status(owner_id, document_id):
    raw = redis_client.hgetall(_status_key(owner_id, document_id))
    if not raw:
        return {}

    for field in ("owner_id", "total_chunks", "embedded_chunks"):
        if field in raw:
            try:
                raw[field] = int(raw[field])
            except (TypeError, ValueError):
                pass

    for field in ("created_at", "updated_at"):
        if field in raw:
            try:
                raw[field] = float(raw[field])
            except (TypeError, ValueError):
                pass

    raw["processing"] = raw.get("status") in PROCESSING_STATUSES
    return raw


def list_document_statuses(owner_id, limit=10):
    document_ids = redis_client.zrevrange(_owner_index_key(owner_id), 0, limit - 1)
    statuses = [
        get_document_status(owner_id, document_id)
        for document_id in document_ids
    ]
    return [status for status in statuses if status]
