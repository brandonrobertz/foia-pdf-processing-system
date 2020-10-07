import os

from collections import OrderedDict


# this is how we decide if a file is complete these are in order, from more
# complete to less.  the way we'll check for complete-ness is to group files
# by name without extension and then find the most complete match based on
# full filename here.
# greater score means higher number of steps required to completion
STATUSES = OrderedDict({
    "complete": lambda n: n.endswith(".cleaned.csv") or n.endswith(".complete.csv"),
    "awaiting-cleaning": lambda n: n.endswith(".csv") or n.endswith(".txt"),
    "awaiting-csv": lambda n: n.endswith(".ocr.pdf"),
    "awaiting-reading": lambda n: n.endswith(".msg"),
    "awaiting-extraction": lambda n: n.endswith(".eml"),
    "unchecked": lambda n: True,
})

STATUS_KEYS = list(STATUSES.keys())
STATUS_SCORES = {st: STATUS_KEYS.index(st) for st in STATUS_KEYS}

STATUS_NAMES = (
    ('complete', 'Complete'),
    ('awaiting-cleaning', 'Awaiting final cleaning'),
    ('awaiting-csv', 'Awaiting conversion to CSV'),
    ('awaiting-reading', 'Awaiting reading/processing'),
    ('awaiting-extraction', 'Awaiting extraction (email)'),
    ('non-request', 'Misc file/unrelated to response'),
    ('unchecked', 'New/Unprocessed'),
)


def document_file_path(instance_or_agency, filename):
    if isinstance(instance_or_agency, str):
        agency = instance_or_agency
    elif hasattr(instance_or_agency, "name"):
        agency = instance.name
    elif hasattr(instance_or_agency, "agency"):
        agency = instance.agency.name
    elif hasattr(instance_or_agency, "document"):
        agency = instance.document.agency.name
    return os.path.join("agency_attachments", agency, filename)
