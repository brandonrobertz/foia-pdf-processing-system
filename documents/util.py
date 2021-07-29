import os

from django.db.models import Model

from collections import OrderedDict


# this is how we decide if a file is complete these are in order, from more
# complete to less.  the way we'll check for complete-ness is to group files
# by name without extension and then find the most complete match based on
# full filename here.
# greater score means higher number of steps required to completion
STATUSES = OrderedDict({
    "complete": lambda n: n.endswith(".cleaned.csv") or n.endswith(".complete.csv"),
    "awaiting-cleaning": lambda n: (n.endswith(".csv") and not n.endswith(".rough.csv")) or n.endswith(".txt") or n.endswith(".precleaned.csv"),
    "awaiting-csv": lambda n: n.endswith(".ocr.pdf"),
    "awaiting-reading": lambda n: n.endswith(".msg"),
    "awaiting-extraction": lambda n: n.endswith(".eml") or n.endswith(".rough.csv"),
    "case-doc": lambda n: False,
    "non-request": lambda n: False, # don't ever match this, but include it for score
    "supporting-document": lambda n: False, # all False status won't be matched
    "exemption-log": lambda n: False,
    "unchecked": lambda n: True,
})

STATUS_KEYS = list(STATUSES.keys())
STATUS_SCORES = {st: STATUS_KEYS.index(st) for st in STATUS_KEYS}
STATUS_NAMES = (
    ('complete', 'Complete'),
    ('awaiting-cleaning', 'Awaiting final cleaning'),
    ('awaiting-csv', 'Awaiting conversion to CSV'),
    ('awaiting-reading', 'Awaiting reading/processing'),
    ('awaiting-extraction', 'Awaiting extraction'),
    ('case-doc', 'Document related to an incident (to be linked/parsed)'),
    ('non-request', 'Misc file/unrelated to response'),
    ('supporting-document', 'Supporting document (complete)'),
    ('exemption-log', 'Exemption log'),
    ('unchecked', 'New/Unprocessed'),
)


def document_file_path(instance_or_agency, filename):
    agency = ''
    if isinstance(instance_or_agency, str):
        agency = instance_or_agency
    elif hasattr(instance_or_agency, "name"):
        agency = instance_or_agency.name
    elif hasattr(instance_or_agency, "agency"):
        agency = instance_or_agency.agency.name
    elif hasattr(instance_or_agency, "document"):
        agency = instance_or_agency.document.agency.name

    path = ''
    if hasattr(instance_or_agency, "document"):
        filepart = instance_or_agency.document.file.name.split(agency)[-1]
        path = os.path.split(filepart)[0].strip("/")

    return os.path.join("agency_attachments", agency, path, filename)
