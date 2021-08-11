#!/usr/bin/env python
import os
import re
from glob import glob
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import tablib

from documents.models import Agency, Document, ProcessedDocument
from documents.util import document_file_path, STATUSES, STATUS_SCORES


PROCESSED_TYPE="Processed"
DOCUMENT_TYPE="Document"


def get_basename_and_ext(filename):
    ext = ''
    basename = filename
    while True:
        _basename, _ext = os.path.splitext(os.path.basename(basename))
        if not _ext:
            basename = _basename
            break
        # only support long extensions for our two known long extension types
        # it's >5 because ext have dot in them
        elif len(_ext) > 5 and _ext not in [".complete", ".cleaned"]:
            break
        ext = f"{_ext}{ext}"
        basename = _basename
    return basename, ext


def normalize_doc_filename(path):
    """
    Take a path to an agency file and strip it down so that it's in
    the proper format as the other documents/processed documents (starts
    with "agency_attachments/").
    """
    return re.sub("^.*/?agency_attachments/", "agency_attachments/", path)


def files_from_agency_dir(agency_dir):
    """
    Return a list of all files in an agency directory path, cleaned in
    the expected document/processed doc format
    """
    files = []
    for x in os.walk(agency_dir):
        for y in glob(os.path.join(x[0], '*'), recursive=True):
            if os.path.isdir(y):
                continue
            
            files.append(normalize_doc_filename(y))
    return sorted(files, reverse=True)


def get_new_agency_files(base_data_dir, only_agency=None, ignore_agencies=None):
    new_agency_files = {}
    for dirname in os.listdir(base_data_dir):
        if dirname.startswith("."):
            continue

        dirpath = os.path.join(base_data_dir, dirname)
        if not os.path.isdir(dirpath):
            continue

        agency = dirname
        if only_agency and agency != only_agency:
            continue

        if ignore_agencies and agency in ignore_agencies:
            continue

        for agency_file in files_from_agency_dir(dirpath):
            try:
                Document.objects.get(
                    file=agency_file, agency__isnull=False
                )
            except Document.DoesNotExist:
                pass
            except Document.MultipleObjectsReturned:
                pass
            else:
                continue

            try:
                ProcessedDocument.objects.get(
                    file=agency_file, document__agency__isnull=False
                )
            except ProcessedDocument.DoesNotExist:
                pass
            except ProcessedDocument.MultipleObjectsReturned:
                pass
            else:
                continue

            # tests for known ignorable files
            # ignore my own request document
            filename = agency_file.split("/")[-1]
            if filename.lower() == "records-request.pdf":
                continue
            elif "exemption log" in filename.lower():
                continue
            elif "redaction log" in filename.lower():
                continue
            elif filename.endswith(".extractor.yaml"):
                continue
            elif filename.endswith(".py"):
                continue
            elif filename.endswith(".sh"):
                continue
            elif filename.endswith(".zip"):
                continue
            elif filename.startswith("."):
                continue
            elif filename.lower() == "joined.csv":
                continue

            # add agency here so we don't iterate over non-new files
            # agencies below
            if agency not in new_agency_files:
                new_agency_files[agency] = []

            new_agency_files[agency].append(agency_file)

    for agency, files in new_agency_files.items():
        files.sort(reverse=True)

    return new_agency_files


def wipe_agency(agency):
    print(f"Wiping agency '{only_agency}'")
    agency = Agency.objects.get(
        name=only_agency
    )
    for doc in agency.document_set.all():
        doc.processeddocument_set.all().delete()
        agency.document_set.all().delete()


def get_page_number_from_filename(filename):
    # NOTE: code fragment! not complete working function
    # set the source page number for a CSV
    found_page_parts = re.findall(r"-p([0-9\-]+)\.csv$", filename)
    if found_page_parts:
        assert len(found_page_parts) == 1
        processed_doc.source_page = found_page_parts[0]
        processed_doc.save()

        # set the source sheet from an XLS for a CSV
        basename, ext = get_basename_and_ext(original_file)
        safe_basename = re.escape(basename)
        sheet_name = re.findall(f"{safe_basename}-(.+)\.csv", filename)
        if sheet_name:
            assert len(sheet_name) == 1
            processed_doc.source_sheet = sheet_name[0]
            processed_doc.save()


def is_definitely_proc_doc(filename):
    # text files are ambiguous
    if filename.endswith(".txt"):
        return False
    proc_doc_statuses = [
        "complete",
        "awaiting-cleaning",
        "awaiting-csv",
    ]
    for status, test in STATUSES.items():
        # test if is in some completion state
        if test(filename) and status in proc_doc_statuses:
            return True


def interactively_find_proc_doc_parent(agency, file):
    parent = None
    while parent is None:
        print(" - Current parent:", parent)
        parent_file = input("Enter the filename of the parent (s to skip): ")
        if parent_file == "s":
            return
        parent = Document.objects.filter(
            agency=agency,
            file=parent_file
        ).first()
        print(" - Found parent:", parent)
    return parent


def is_definitely_responsive_doc(file):
    lfile = file.lower()
    if lfile.endswith(".pdf"):
        return True
    if lfile.endswith(".xlsx"):
        return True
    if lfile.endswith(".doc"):
        return True
    if lfile.endswith(".docx"):
        return True
    if lfile.endswith(".msg"):
        return True
    if lfile.endswith(".eml"):
        return True
    if lfile.endswith(".mp3"):
        return True
    if lfile.endswith(".wma"):
        return True


def add_doc_by_type(mtype, agency, file):
    assert agency, f"No agency passed when creating file: {file}!"
    if mtype == DOCUMENT_TYPE:
        print(" - Adding as document")
        Document.objects.create(
            agency=agency,
            file=file
        )
    elif mtype == PROCESSED_TYPE:
        possible_parent = file
        strip_extensions = [
            ".cleaned.csv", ".complete.csv", ".rough.csv",
            ".precleaned.csv", ".ocr.pdf", ".rough.csv",
            # these ones can be dangerous is there's multiple .ext.ext
            ".csv", ".txt",
        ]
        for ext in strip_extensions:
            if possible_parent.endswith(ext):
                possible_parent = possible_parent.replace(ext, "")
        print(" - Looking for parent with prefix:", possible_parent)
        docs = Document.objects.filter(
            agency=agency,
            file__startswith=possible_parent,
        )
        parent = None
        if docs.count() == 1:
            parent = docs[0]
        elif docs.count() == 0:
            print(f" - Couldn't find parent for file: {file}")
            parent = interactively_find_proc_doc_parent(agency, file)
        else:
            print(f" - Found possible parents:")
            for ix in range(len(docs)):
                d = docs[ix]
                print("    -", ix, d.file)
            p_ix = int(input("Which file is the parent? (enter number) "))
            parent = docs[p_ix]

        if parent is None:
            print(f" - Couldn't find parent for file: {file}")
        else:
            print(" - Adding as processed doc")
            print(" - Parent:", parent)
            ProcessedDocument.objects.create(
                document=parent,
                file=file,
            )
    else:
        print(f"ERROR: Couldn't add file with type: {mtype}")


class Command(BaseCommand):
    help = """Scan agency directory, copying and setting up the database. This command will optionally output a CSV if the second arg is provided."""

    def add_arguments(self, parser):
        parser.add_argument('base_data_dir', type=str)
        parser.add_argument(
            '--agency', type=str,
            help='Only use handle data for this agency (based on agency folder)'
        )
        parser.add_argument(
            '--ignore', type=str,
            help='Ignore these agencies (comma separated)'
        )

    def handle(self, *args, **options):
        base_data_dir = options['base_data_dir']
        only_agency = options.get('agency')
        ignore_str = options.get('ignore') or ""
        ignore_agencies = [
            a.strip() for a in ignore_str.strip().split(",")
            if a.strip()
        ]

        print("Importing with args:")
        print(f"    Base data directory: {base_data_dir}")
        print(f"    Only agency: {only_agency}")
        print(f"    Ignore agencies: {ignore_agencies}")


        print("Searching for new agency files...")
        new_agency_files = get_new_agency_files(
            base_data_dir, only_agency=only_agency,
            ignore_agencies=ignore_agencies
        )
        print(f"Found new files from {len(new_agency_files)} agencies")

        for agency_name, files in new_agency_files.items():
            agency = None
            try:
                agency = Agency.objects.get(name=agency_name)
                print(f"\nAgency '{agency_name}'")
            except Agency.DoesNotExist:
                print(f"\nAgency '{agency_name}' doesn't exist.")
                print(" - New files:")
                for f in files:
                    print(f"   - {f}")
                yn = input(f"Create '{agency_name}'? (y/n) ")
                if yn.lower() == "y":
                    agency = Agency.objects.create(
                        name=agency_name
                    )
                    pop = Agency.try_to_get_population(agency_name)
                    if not pop:
                        print(" - Couldn't automatically find population.")
                        try:
                            pop = int(input("Enter population: "))
                        except Exception as e:
                            print(" ! Parse error:", e)
                            print(" - Not adding population.")
                            pop = None
                    if pop:
                        agency.population = pop
                    agency.save()
                    print(" - Created agency!")
                else:
                    continue

            for file in files:
                mtype = None
                # check this first as .pdf will get caught for document, when
                # in fact ocr.pdf is a processed doc
                if is_definitely_proc_doc(file):
                    mtype = PROCESSED_TYPE
                elif is_definitely_responsive_doc(file):
                    mtype = DOCUMENT_TYPE
                else:
                    print(" - Can't figure out what type of doc this is:")
                    print(file)
                    pd = input(
                        f"What type is it? (p)rocessed, (d)ocument or (s)kip "
                    ).lower().strip()

                    if pd == "s":
                        print(" - Skipping file")
                        continue
                    elif pd == "d":
                        mtype = DOCUMENT_TYPE
                    elif pd == "p":
                        mtype = PROCESSED_TYPE
                    # this should be a catch all
                    elif pd not in ["p", "d"]:
                        print(" - Unrecognized option! Skipping file.")
                        continue

                print(f" - New file: {file} Type: {mtype}")
                add_doc_by_type(mtype, agency, file)


        print("Complete!")
