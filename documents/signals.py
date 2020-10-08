from django.core.signals import post_save
from django.dispatch import receiver

from .util import STATUS_SCORES
from .models import ProcessedDocument


@receiver(post_save, sender=ProcessedDocument)
def update_document_status(sender, **kwargs):
    """
    Keep a document's status in sync with its most processed document.
    """
    instance = kwargs['instance']
    document = instance.document

    # dict, {score: processed, ...}
    scores = {}
    for proc in document.processeddocument_set.all():
        score = STATUS_SCORES[proc.status]
        scores[score] = proc

    most_complete_score = min(scores.keys())
    most_complete_proc = scores[most_complete_score]

    document.status = most_complete_proc.status
    document.save()
