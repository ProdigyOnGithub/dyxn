import uuid
from task_queue.producer import enqueue_document

def upload_doc(document_id, path, owner_id, source_type):

    enqueue_document(
        document_id=document_id,
        owner_id=owner_id,
        path=path,
        source_type=source_type
    )

    return document_id