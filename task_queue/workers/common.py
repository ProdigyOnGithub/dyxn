import json
import logging
import time

from redis.exceptions import RedisError, ResponseError, TimeoutError as RedisTimeoutError

from core.document_status import mark_document_failed
from core.redis import redis_client


MAX_RETRIES = 3
READ_BLOCK_MS = 5000


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_consumer_group(stream: str, group: str, logger: logging.Logger):
    try:
        redis_client.xgroup_create(stream, group, id="0", mkstream=True)
        logger.info("Created Redis consumer group stream=%s group=%s", stream, group)
    except ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            logger.info(
                "Redis consumer group already exists stream=%s group=%s",
                stream,
                group,
            )
            return
        raise


def wait_for_consumer_group(stream: str, group: str, logger: logging.Logger):
    while True:
        try:
            create_consumer_group(stream, group, logger)
            return
        except ResponseError:
            raise
        except RedisError:
            logger.exception(
                "Redis unavailable while creating consumer group stream=%s group=%s; retrying",
                stream,
                group,
            )
            time.sleep(5)


def read_new_messages(stream: str, group: str, consumer: str, logger: logging.Logger):
    try:
        return redis_client.xreadgroup(
            group,
            consumer,
            {stream: ">"},
            count=1,
            block=READ_BLOCK_MS,
        )
    except RedisTimeoutError:
        logger.debug(
            "Redis stream read timed out stream=%s group=%s consumer=%s",
            stream,
            group,
            consumer,
        )
        redis_client.connection_pool.disconnect()
        return []
    except RedisError:
        logger.exception("Redis read failed stream=%s group=%s consumer=%s", stream, group, consumer)
        time.sleep(5)
        return []


def decode_payload(data):
    raw_payload = data.get("data")
    if raw_payload is None:
        raise ValueError("Redis stream message is missing 'data'")

    payload = json.loads(raw_payload)
    if not isinstance(payload, dict):
        raise ValueError("Redis stream message data must decode to a JSON object")

    return payload


def ack_message(stream: str, group: str, msg_id):
    redis_client.xack(stream, group, msg_id)


def handle_processing_failure(
    *,
    stream: str,
    group: str,
    msg_id,
    data,
    exc: Exception,
    logger: logging.Logger,
    max_retries: int = MAX_RETRIES,
):
    try:
        payload = decode_payload(data)
    except Exception:
        payload = {"raw_data": data.get("data")}

    attempts = int(payload.get("_attempts", 0)) + 1
    payload["_attempts"] = attempts
    payload["_last_error"] = str(exc)

    if attempts <= max_retries:
        redis_client.xadd(stream, {"data": json.dumps(payload, default=str)})
        logger.exception(
            "Message processing failed; requeued stream=%s group=%s msg_id=%s attempt=%s/%s",
            stream,
            group,
            msg_id,
            attempts,
            max_retries,
        )
    else:
        failed_stream = f"{stream}_failed"
        redis_client.xadd(
            failed_stream,
            {
                "data": json.dumps(
                    {
                        "stream": stream,
                        "group": group,
                        "original_msg_id": msg_id,
                        "error": str(exc),
                        "payload": payload,
                    },
                    default=str,
                )
            },
        )
        logger.exception(
            "Message processing failed permanently; moved to dead-letter stream=%s msg_id=%s",
            failed_stream,
            msg_id,
        )
        try:
            mark_document_failed(
                payload.get("owner_id"),
                payload.get("document_id"),
                exc,
            )
        except Exception:
            logger.exception("Failed to update document failure status msg_id=%s", msg_id)

    ack_message(stream, group, msg_id)
