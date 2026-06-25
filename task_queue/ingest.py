import uuid

from task_queue.producer import enqueue_document


def upload_document(path, owner_id, source_type):
    document_id = uuid.uuid4().hex
    enqueue_document(
        document_id=document_id,
        owner_id=owner_id,
        path=path,
        source_type=source_type,
    )

    return document_id
