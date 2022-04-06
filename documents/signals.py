from django.db.models.signals import post_save
from django.dispatch import receiver

from .util import STATUS_SCORES
from .models import Document, ProcessedDocument, SyntheticDocument


def update_doc_status(document):
    """
    Keep a document's status in sync with its most processed document.
    """
    # don't update if we've set to one of these
    if document.status in ["complete", "case-doc",
                           "supporting-document", "non-request"]:
        return

    for syndoc in document.syntheticdocument_set.all():
        if not syndoc.completed:
            continue
        document.status = "complete"
        document.save()
        return

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
    if not document.no_new_records and not document.status == "complete":
        update_doc_status(document)

@receiver(post_save, sender=SyntheticDocument)
def update_synthetic_dependent_status(sender, **kwargs):
    syn_document = kwargs['instance']
    print("syn_document", syn_document)
    if not syn_document.completed:
        print("not completed")
        return
    for document in syn_document.documents.all():
        print(document.id, "document", document, "status", document.status, "file", document.file)
        # if document.status == "complete": continue
        document.status = "complete"
        document.save()
    for p_document in syn_document.processed_documents.all():
        print(p_document.id, "p_document", p_document, "status", p_document.status)
        print(p_document.document.id, "p_document.document", p_document.document, "status", p_document.document.status, "file", p_document.document.status)
        # if p_document.document.status == "complete": continue
        p_document.document.status = "complete"
        p_document.document.save()
