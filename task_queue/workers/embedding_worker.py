import json
import logging

from core.document_status import mark_chunk_embedded, update_document_status
from core.redis import redis_client
from ingestion.embedding import embed_text
from ingestion.ingest import upsert_chunk
from task_queue.workers.common import (
    ack_message,
    configure_logging,
    decode_payload,
    handle_processing_failure,
    read_new_messages,
    wait_for_consumer_group,
)

STREAM = "embedding_queue"
GROUP = "embedders"
CONSUMER = "embedder_1"
logger = logging.getLogger(__name__)


def process_message(msg_id, data):
    payload = decode_payload(data)
    update_document_status(
        payload["owner_id"],
        payload["document_id"],
        status="embedding",
    )
    vector = embed_text(payload["text"])
    chunk_id = payload["chunk_id"]

    upsert_chunk(
        chunk_id=chunk_id,
        embedding=vector,
        payload=payload,
    )

    mark_chunk_embedded(payload["owner_id"], payload["document_id"])
    ack_message(STREAM, GROUP, msg_id)
    logger.info(
        "Embedded chunk_id=%s document_id=%s source_type=%s",
        chunk_id,
        payload["document_id"],
        payload["source_type"],
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
