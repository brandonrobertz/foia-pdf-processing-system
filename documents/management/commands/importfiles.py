#!/usr/bin/env python
import os
import re
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import tablib

from documents.models import Agency, Document, ProcessedDocument
from documents.util import document_file_path, STATUSES, STATUS_SCORES


def get_status(files_group, basepath=None, agency=None):
    s_fn = lambda n: os.path.getmtime(os.path.join(basepath, agency, n))
    sorted_files = sorted(files_group, key=s_fn, reverse=True)

    final_status = None
    lowest_score = None
    original_file = sorted_files.pop()
    current_file = None
    for filename in files_group:
        for status, test_fn in STATUSES.items():
            if test_fn(filename):
                score = STATUS_SCORES[status]
                if lowest_score is None or lowest_score > score:
                    lowest_score = score
                    final_status = status
                    current_file = filename
                break

    # PDF Pre-processing correction: we have a page-extracted file here, so we
    # add the original file (without the -p[num]) suffix.
    found_page_parts = re.findall(r"-p[0-9\-]+\.[a-zA-Z]{3,}$", current_file)
    if found_page_parts:
        assert len(found_page_parts) == 1
        page_part_w_ext = found_page_parts[0]
        ext = page_part_w_ext.split('.')[-1]
        original_file = current_file.replace(page_part_w_ext, "") + ".pdf"

    return final_status, current_file, original_file


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


def get_file_groups(agency_files):
    # basename: filenames
    groups = {}
    for file in sorted(agency_files):
        basename, ext = get_basename_and_ext(file)
        if basename not in groups:
            groups[basename] = []
        groups[basename].append(file)
    remove_groups = []
    for basename, group in groups.items():
        for file in group:
            # combine [name].xls and its [name]-[sheet].csv files
            if ".xls" in file:
                for basename2, group2 in groups.items():
                    if basename == basename2:
                        continue
                    for file2 in group2:
                        if re.findall(f"{basename}-.+\.csv", file2):
                            # add the base xls/x file to the sheetgroup
                            group2.append(file)
                            # we have a match on the base XLS, so don't add
                            # it as its own group
                            if basename not in remove_groups:
                                remove_groups.append(basename)
            # combine [name].docx and its [name]_[table_no].csv files
            elif ".docx" in file:
                for basename2, group2 in groups.items():
                    if basename == basename2:
                        continue
                    for file2 in group2:
                        if re.findall(f"{basename}_.+\.csv", file2):
                            # add the base xls/x file to the sheetgroup
                            group2.append(file)
                            # we have a match on the base XLS, so don't add
                            # it as its own group
                            if basename not in remove_groups:
                                remove_groups.append(basename)

    for basename in remove_groups:
        del groups[basename]

    for basename in groups.keys():
        groups[basename].sort()

    return groups


def get_agency_files(base_data_dir, only_agency=None, ignore_agencies=None):
    cleaned_agency_files = {}
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

        for basedir, _, files in os.walk(dirpath):
            # if we're in a subdirectory of a agency directory, get
            # the relative path to our files
            dir_part = ''
            end_position = basedir.index(agency) + len(agency)
            # if we have another folder, we'll have at least '/' and 
            # a (minimum one char) folder appended
            if len(basedir) >= end_position + 2:
                # we have subdirs, add it to basedir
                dir_part = basedir[end_position + 1:]

            for name in files:
                # ignore my own request document
                if name.lower() == "records-request.pdf":
                    continue
                elif "exemption log" in name.lower():
                    continue
                elif "redaction log" in name.lower():
                    continue
                elif name.endswith(".extractor.yaml"):
                    continue
                elif name.endswith(".py"):
                    continue
                elif name.endswith(".sh"):
                    continue
                elif name.endswith(".zip"):
                    continue
                elif name.startswith("."):
                    continue
                elif name.lower() == "joined.csv":
                    continue
                if agency not in cleaned_agency_files:
                    cleaned_agency_files[agency] = []
                rel_path = os.path.join(dir_part, name)
                cleaned_agency_files[agency].append(rel_path)

    return cleaned_agency_files

class Command(BaseCommand):
    help = """Scan agency directory, copying and setting up the database. This command will optionally output a CSV if the second arg is provided."""

    def add_arguments(self, parser):
        parser.add_argument('base_data_dir', type=str)
        parser.add_argument(
            '--agency', type=str,
            help='Only use handle data for this agency (based on agency folder)'
        )
        parser.add_argument(
            '--wipe-agency', action='store_true',
            help=(
                'Clears all files from an agency before importing. Can only '
                'be used with --agency'
            )
        )
        parser.add_argument(
            '--dryrun-output', type=str,
            help='Ouput CSV instead of writing to DB/copying files'
        )

    def handle(self, *args, **options):
        base_data_dir = options['base_data_dir']
        only_agency = options.get('agency')
        wipe_agency = None
        if only_agency:
            wipe_agency = options.get('wipe_agency', None)
        output_csv = options.get('dryrun-output')

        print("Importing with args:")
        print(f"    Only agency: {only_agency}")
        print(f"    Wipe agency: {wipe_agency}")
        print(f"    Dryrun, output to CSV: {output_csv}")

        # if os.path.exists(output_csv):
        #     with open(output_csv, "r") as f:
        #         data = tablib.Dataset.load(f.read(), format='csv')
        # else:
        headers = ("status", "agency", "current_file", "original_file")
        data = tablib.Dataset(headers=headers)

        existing = set()
        for row in data.dict:
            agency = row["agency"]
            name = row["original_file"]
            unique_hash = f"{agency}-{name}"
            existing[unique_hash] = True

        ignore_agencies = [
            'Kennewick Police Department',
        ]

        # {agency-original_filename: [file1, file2, ..., fileN]}
        agency_middle_files = {}
        agency_files = get_agency_files(base_data_dir, only_agency=only_agency,
                                        ignore_agencies=ignore_agencies)
        for agency, files in agency_files.items():
            for basename, group in get_file_groups(files).items():
                status, current_filename, original_filename = get_status(
                    group, basepath=base_data_dir, agency=agency
                )

                unique_hash = f"{agency}-{original_filename}"
                if unique_hash in existing:
                    print("Skipping eixsting agency file", agency, original_filename)
                    continue
                data.append((status, agency, current_filename, original_filename))

                # skip XLS groups because they're more complicated
                agency_ogname_key = f"{agency}-{original_filename}"
                agency_middle_files[agency_ogname_key] = []
                if ".xls" not in original_filename.lower():
                    for filename in group:
                        if filename != current_filename and filename != original_filename:
                            agency_middle_files[agency_ogname_key].append(filename)

        if output_csv:
            try:
                os.rename(output_csv, f"{output_csv}.bak")
            except FileNotFoundError:
                pass

            with open(output_csv, "w") as f:
                f.write(data.csv)

            # all done here, don't write results to DB or copy files
            return

        if wipe_agency:
            print(f"Wiping agency '{only_agency}'")
            agency = Agency.objects.get(
                name=only_agency
            )
            for doc in agency.document_set.all():
                doc.processeddocument_set.all().delete()

            agency.document_set.all().delete()

        for row in data.dict:
            agency, created = Agency.objects.get_or_create(
                name=row["agency"]
            )
            if created:
                print("Created agency", agency)

            original_file = row["original_file"]
            current_file = row["current_file"]
            status = row["status"]

            document, created = Document.objects.get_or_create(
                agency=agency,
                file=document_file_path(agency.name, original_file)
            )
            if created:
                print("Created document", document)
                print("  - Doc agency", agency)

            middle_filenames = agency_middle_files[f"{agency.name}-{original_file}"]
            for middle_filename in middle_filenames:
                m_proc_doc, created = ProcessedDocument.objects.get_or_create(
                    document=document,
                    file=document_file_path(agency.name, middle_filename),
                )
                if created:
                    print("Created middle processed document", m_proc_doc)
                    print("  - Parent document", document)

            if current_file != original_file:
                processed_doc, created = ProcessedDocument.objects.get_or_create(
                    document=document,
                    file=document_file_path(agency.name, current_file),
                )
                if created:
                    print("Created processed document", processed_doc)
                    print("  - Parent document", document)

                processed_doc.save()

            # set the source page number for a CSV
            found_page_parts = re.findall(r"-p([0-9\-]+)\.csv$", current_file)
            if found_page_parts:
                assert len(found_page_parts) == 1
                processed_doc.source_page = found_page_parts[0]
                processed_doc.save()

            # set the source sheet from an XLS for a CSV
            basename, ext = get_basename_and_ext(original_file)
            safe_basename = re.escape(basename)
            sheet_name = re.findall(f"{safe_basename}-(.+)\.csv", current_file)
            if sheet_name:
                assert len(sheet_name) == 1
                processed_doc.source_sheet = sheet_name[0]
                processed_doc.save()

        print("Complete!")
