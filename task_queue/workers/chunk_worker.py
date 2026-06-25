import json
import logging

from core.document_status import update_document_status
from core.redis import redis_client
from chunking.pipeline import build_chunks
from task_queue.workers.common import (
    ack_message,
    configure_logging,
    decode_payload,
    handle_processing_failure,
    read_new_messages,
    wait_for_consumer_group,
)

STREAM = "document_ingestion"
OUTPUT_STREAM = "embedding_queue"
GROUP = "chunkers"
CONSUMER = "worker_1"
logger = logging.getLogger(__name__)


def _embedding_payload(document_payload, chunk, chunk_index):
    if isinstance(chunk, str):
        text = chunk
        metadata = {}
    elif isinstance(chunk, dict):
        text = chunk.get("text", "")
        metadata = {
            "source_file": chunk.get("source_file"),
            "page": chunk.get("page"),
            "heading": chunk.get("heading"),
            "source_chunk_id": chunk.get("chunk_id"),
        }
    else:
        raise TypeError(f"Unsupported chunk type: {type(chunk).__name__}")

    if not isinstance(text, str) or not text.strip():
        raise ValueError(f"Chunk {chunk_index} does not contain valid text")

    payload = {
        "document_id": document_payload["document_id"],
        "owner_id": document_payload["owner_id"],
        "chunk_index": chunk_index,
        "chunk_id": f"{document_payload['document_id']}_{chunk_index}",
        "source_type": document_payload["source_type"],
        "text": text,
    }

    payload.update({key: value for key, value in metadata.items() if value is not None})
    return payload


def process_message(msg_id, data):
    payload = decode_payload(data)
    update_document_status(
        payload["owner_id"],
        payload["document_id"],
        status="chunking",
    )
    chunks = build_chunks(payload["path"], payload["source_type"])

    embedding_payloads = [
        _embedding_payload(payload, chunk, i)
        for i, chunk in enumerate(chunks)
    ]
    if not embedding_payloads:
        raise ValueError(f"No chunks generated for document_id={payload['document_id']}")

    pipeline = redis_client.pipeline(transaction=True)
    for embedding_payload in embedding_payloads:
        pipeline.xadd(
            OUTPUT_STREAM,
            {"data": json.dumps(embedding_payload)},
        )
    pipeline.execute()
    update_document_status(
        payload["owner_id"],
        payload["document_id"],
        status="embedding",
        total_chunks=len(embedding_payloads),
        embedded_chunks=0,
    )

    ack_message(STREAM, GROUP, msg_id)
    logger.info(
        "Chunked document_id=%s source_type=%s chunks=%s",
        payload["document_id"],
        payload["source_type"],
        len(embedding_payloads),
    )


def run():
    configure_logging()
    wait_for_consumer_group(STREAM, GROUP, logger)

    while True:
        messages = read_new_messages(STREAM, GROUP, CONSUMER, logger)

        if not messages:
            continue

        for _, entries in messages:
            for msg_id, data in entries:
                try:
                    process_message(msg_id, data)
                except Exception as exc:
                    handle_processing_failure(
                        stream=STREAM,
                        group=GROUP,
                        msg_id=msg_id,
                        data=data,
                        exc=exc,
                        logger=logger,
                    )


if __name__ == "__main__":
    run()
