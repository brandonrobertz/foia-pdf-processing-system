from django.db.models.signals import post_save
from django.dispatch import receiver

from .util import STATUS_SCORES
from .models import Document, ProcessedDocument


def update_doc_status(document):
    """
    Keep a document's status in sync with its most processed document.
    """
    processed = document.processeddocument_set.all()
    if not processed.count():
        return

    # dict, {score: processed, ...}
    scores = {}
    for proc in processed:
        score = STATUS_SCORES[proc.status]
        scores[score] = proc

    most_complete_score = min(scores.keys())
    most_complete_proc = scores[most_complete_score]

    if most_complete_proc.status != document.status:
        document.status = most_complete_proc.status
        document.save()


@receiver(post_save, sender=ProcessedDocument)
def update_document_status_from_processed(sender, **kwargs):
    instance = kwargs['instance']
    update_doc_status(instance.document)


@receiver(post_save, sender=Document)
def update_document_status(sender, **kwargs):
    document = kwargs['instance']
    # only override status if file is marked as no records
    # this means this document will never have a completed status
    if not document.no_new_records:
        update_doc_status(document)
