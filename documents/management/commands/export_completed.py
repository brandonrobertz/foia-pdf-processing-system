#!/usr/bin/env python
import csv
import codecs
import itertools
import json
import os
import re
import sys

from django.core.management.base import BaseCommand
import ftfy
import numpy as np
import sqlite3
import sqlite_utils
import tablib

from documents.models import Agency, Document, ProcessedDocument


csv.field_size_limit(sys.maxsize)


DOCUMENT_TYPES = [
    "collisions",
    "complaints",
    "internal investigations",
    "unofficial investigations",
    # catch-all
    "reprimands-warnings",
]
# where to output our databases
OUTPUT_DIRECTORY="./data/wa_pd_databases"


def matrix(a, b, match_score=3, gap_cost=2):
    H = np.zeros((len(a) + 1, len(b) + 1))
    i_range = range(1, H.shape[0])
    j_range = range(1, H.shape[1])
    for i, j in itertools.product(i_range, j_range):
        score = match_score if a[i - 1] == b[j - 1] else -match_score
        match = H[i - 1, j - 1] + score
        delete = H[i - 1, j] - gap_cost
        insert = H[i, j - 1] - gap_cost
        H[i, j] = max(match, delete, insert, 0)
    return H


def traceback(H, b, b_='', old_i=0):
    # flip H to get index of **last** occurrence of H.max() with np.argmax()
    H_flip = np.flip(np.flip(H, 0), 1)
    i_, j_ = np.unravel_index(H_flip.argmax(), H_flip.shape)
    # (i, j) are **last** indexes of H.max()
    i, j = np.subtract(H.shape, (i_ + 1, j_ + 1)) 
    if H[i, j] == 0:
        return b_, j
    b_ = b[j - 1] + '-' + b_ if old_i - i > 1 else b[j - 1] + b_
    return traceback(H[0:i, 0:j], b, b_, i)


def smith_waterman(a, b, match_score=3, gap_cost=2):
    """
    Find the longest common substring between two strings, a and b.
    """
    a, b = a.lower(), b.lower()
    H = matrix(a, b, match_score, gap_cost)
    b_, pos = traceback(H, b)
    return a[pos: pos + len(b_)]


def damerau_levenshtein_similarity(a, b):
    # "Infinity" -- greater than maximum possible edit distance
    # Used to prevent transpositions for first characters
    INF = len(a) + len(b)

    # Matrix: (M + 2) x (N + 2)
    matrix  = [[INF] * (len(b) + 2)]
    matrix += [[INF] + list(range(len(b) + 1))]
    matrix += [[INF, m] + [0] * len(b) for m in range(1, len(a) + 1)]

    # Holds last row each element was encountered: DA in the Wikipedia pseudocode
    last_row = {}

    # Fill in costs
    for row in range(1, len(a) + 1):
        # Current character in a
        ch_a = a[row-1]

        # Column of last match on this row: DB in pseudocode
        last_match_col = 0

        for col in range(1, len(b) + 1):
            # Current character in b
            ch_b = b[col-1]

            # Last row with matching character
            last_matching_row = last_row.get(ch_b, 0)

            # Cost of substitution
            cost = 0 if ch_a == ch_b else 1

            # Compute substring distance
            matrix[row+1][col+1] = min(
                matrix[row][col] + cost, # Substitution
                matrix[row+1][col] + 1,  # Addition
                matrix[row][col+1] + 1,  # Deletion

                # Transposition
                # Start by reverting to cost before transposition
                matrix[last_matching_row][last_match_col]
                    # Cost of letters between transposed letters
                    # 1 addition + 1 deletion = 1 substitution
                    + max((row - last_matching_row - 1),
                          (col - last_match_col - 1))
                    # Cost of the transposition itself
                    + 1)

            # If there was a match, update last_match_col
            if cost == 0:
                last_match_col = col

        # Update last row for current character
        last_row[ch_a] = row

    # last element is the difference
    dl_diff = matrix[-1][-1]

    # this gives us a 1-0 scale of similarity where 1 is exactly
    # equal and 0 is totally different
    return 1 - (dl_diff / max(len(a), len(b)))


# https://stackoverflow.com/a/18048211
def print_table(seq, columns=3):
    if len(seq) <= 1:
        print("\n".join(seq))
    table = ''
    col_height = int(len(seq) / columns)
    for x in range(col_height):
        for col in range(columns):
            pos = (x * columns) + col
            num = seq[x + (col_height * col)].replace("\n", "")
            table += (' %s: %s' % (pos, num)).ljust(40)
        table += '\n'
    print(table.strip('\n'))


def clean_headers(headers):
    if isinstance(headers, str):
        headers = [headers]
    cleaned_headers = []
    for raw_h in headers:
        cleaned_headers.append(re.sub(
            f"\s+", " ", raw_h.lower().replace(
                "recevied", "received"
            )
        ).strip())
    return cleaned_headers


class Command(BaseCommand):
    help = """
    Looks through all the completed/csv records and counts the number
    of rows. This is just to give an approximate number of total IA
    records we've processed.
    """

    prompt = True
    def should_continue(self):
        yn = input("Continue? [Y]es/(n)o/(a)ll ").lower()
        if yn == "n":
            sys.exit(1)
        elif yn == "a":
            self.prompt = False

    def convert_processed_doc(self, pdoc):
        with codecs.open(pdoc.file.path, encoding='utf-8-sig') as f:
            # If file starts with (UTF-8 BOM): 0xEFBBBF4F
            # >>> with codecs.open('excel_output.csv', encoding='utf-8-sig') as f:
            # ...     reader = csv.reader(f)
            # ...     rows = [row for row in reader]
            try:
                csv = tablib.Dataset().load(f, format="csv")
            # except UnicodeDecodeError as e:
            #     ftfy.fix_encoding()
            except Exception as e:
                print("ERROR While reading file:", pdoc.file.name)
                print("ProcessedDocument:", pdoc)
                raise e

            if not len(csv):
                print("No rows in CSV, returning without processing.")
                return

            self.total_rows += len(csv)
            for h in csv.headers:
                self.filename_headers.append([pdoc.file.name, h])

            print("Processed Document:", pdoc)
            print("Rows:", len(csv))
            print("Headers:", csv.headers)
            print_table(csv.headers)

            for row in csv.dict:
                self.all_rows.append(row)
            return csv

    def table_name_from_filenames(self, filenames):
        common_name = filenames[0]
        if len(filenames) >= 2:
            a = filenames[0]
            b = smith_waterman(a, filenames[1])
            for a in filenames[2:]:
                b = smith_waterman(a, b)
            common_name = b
        table_name = re.sub(
            r"^[\s\-_]+|[\s\-_]+$", "", common_name.rsplit(
                ".", 2
            )[0].rsplit("/", 1)[-1].replace(".", "_")
        ).strip()
        if not table_name:
            return "incidents"
        return table_name

    def write_database(self, agency, table, csv, unified_headers,
                       filename=None):
        print("=" * 10)
        print("Table:", table)
        print("Filename:", filename)
        print("Unified Headers:", len(unified_headers), unified_headers)
        print("CSV Headers:", len(csv.headers), csv.headers)
        std_unified_headers = clean_headers(unified_headers)
        std_file_headers = clean_headers(csv.headers)

        # get the overall headers not in our file headers
        diffs = set(std_unified_headers).difference(set(std_file_headers))
        # do a check to make sure we don't have any weird misalignments
        if len(diffs):
            for i, std_file_h in enumerate(std_file_headers):
                file_h = csv.headers[i]
                std_uni_h = unified_headers[i]
                print(i, "std file:", std_file_h, "std_uni:", std_uni_h, "file h:", file_h)
                if std_file_h != std_uni_h:
                    if input("Header mismatch. Enter debugger? y/n ") == "y":
                        import pdb
                        pdb.set_trace()

        # a fix for the first column with a blank name, which was caused
        # by the XLS to CSV exporter leaving the row number in the CSV but
        # not giving it a header for some reason
        csv.headers = std_file_headers
        if not csv.headers[0] and "file_row" not in csv.headers:
            csv.headers[0] = "file_row"

        for row in csv.dict:
            table.insert(row, alter=True)

    def process_agency(self, agency):
        # a sequence we'll use to join and split headers pre/post cleaning
        # it should be something that won't naturally be found in headers
        JOIN_SEQ = "-~=~-"
        EXPORT_STATUSES = ["complete", "auto-extracted", "case-doc"]

        agency_complete_docs = Document.objects.filter(
            status__in=EXPORT_STATUSES,
            # skip these, they don't have data, even if marked complete
            no_new_records=False,
            agency=agency,
        )

        if not agency_complete_docs.count():
            print("No complete documents for", agency.name)
            return 0

        print()
        print("=" * 78)
        print("Agency:", agency.name)
        print(f"{agency_complete_docs.count()} completed document(s)")

        filename_csv_lookup = {}
        agency_filenames = []
        agency_csvs = []

        # store IDs for deduplication
        pdocs_ids_seen = set()
        for doc in agency_complete_docs:
            # process PDF/Excel that got converted to CSV via processed doc
            if not doc.file.name.endswith(".csv"):
                for pdoc in doc.processeddocument_set.filter(status__in=EXPORT_STATUSES):
                    if not pdoc.file:
                        print("!", "ERROR: skipping blank Processed Doc",
                              pdoc, "Skipping.")
                        continue

                    print("Adding pdoc:", pdoc)

                    if pdoc.id in pdocs_ids_seen:
                        continue

                    pdocs_ids_seen.add(pdoc.id)

                    # with pdoc.file.open(mode='r', encoding='utf-8-sig') as f:
                    csv = self.convert_processed_doc(pdoc)
                    if csv and (pdoc.file.name not in agency_filenames):
                        self.total_rows += len(csv)
                        agency_filenames.append(pdoc.file.name)
                        agency_csvs.append(csv)
                        filename_csv_lookup[pdoc.file.name] = csv

        # now we have a list of CSVs, let's try and find ones with
        # duplicate headers and join them together
        # header_row => [csv_filename1, ..., csv_filenameN]
        headers_seen = {}
        for ix, csv in enumerate(agency_csvs):
            cleaned_headers = clean_headers(csv.headers)
            header_text = JOIN_SEQ.join(cleaned_headers)
            if header_text not in headers_seen:
                headers_seen[header_text] = []
            headers_seen[header_text].append(agency_filenames[ix])

        # print()
        # print("Headers Seen #1")
        # print(json.dumps(headers_seen, indent=2))

        # now we do a second pass, ordered alphabetically, and
        # merge headers that start with the preceeding headers
        header_keys = sorted(headers_seen.keys())
        for ix, header_text in enumerate(header_keys):
            # skip the first as we compare backwards
            if ix == 0:
                continue
            # skip headers we've already joined
            if header_text not in headers_seen:
                continue
            header_prev = header_keys[ix-1]
            if header_text.startswith(header_prev):
                # add the previous, shorter header, to this new longer,
                # but otherwise the same one
                headers_seen[header_text] += headers_seen.pop(header_prev)

        # TODO: similar to the below, where we add new columns, if most
        # of the columns are matching, here we want to check for columns
        # that are the same except for a typo/etc
        # NOTE: if we do this then we have to keep track of the
        # original headers that map to a single header
        # TODO: handle small typos/etc as long we we have
        # the same number of columns

        # merge headers that only have one or maybe two completely
        # different columns?
        header_keys = sorted(headers_seen.keys())
        for ix1, header_text1 in enumerate(header_keys):
            headers_set1 = set(header_text1.split(JOIN_SEQ))
            best_match = None
            for ix2, header_text2 in enumerate(header_keys):
                if ix1 == ix2 or header_text1 == header_text1:
                    continue
                # skip headers we've already joined
                if header_text1 not in headers_seen:
                    continue
                if header_text2 not in headers_seen:
                    continue

                headers_set2 = set(header_text2.split(JOIN_SEQ))
                # only move forward if we have a header1 that
                # is smaller than 2, since header1 gets rolled into
                # header2 which needs to be larger
                if len(headers_set1) > len(headers_set2):
                    continue

                diff = headers_set2.difference(headers_set1)
                if len(diff) <= 2:
                    headers_seen[header_text2] += headers_seen.pop(header_text1)

        # print()
        # print("Headers Seen #2")
        # print(json.dumps(headers_seen, indent=2))

        n_original = len(agency_csvs)
        n_combined = len(headers_seen.keys())
        if n_original == n_combined:
            print("No CSVs merged.") 
        else:
            print("*" * 50)
            print(f"CSVs merged! Originally {n_original}, now {n_combined}")
            for header_text, filenames in headers_seen.items():
                print("~" * 50)
                header_array = header_text.split(JOIN_SEQ)
                if len(filenames) == 1:
                    print("Single File:", filenames[0])
                else:
                    print(f"Group of {len(filenames)} files:")
                    print_table(
                        [f.rsplit("/", 1)[-1] for f in filenames],
                        columns=1
                    )
                print("Headers:")
                print_table(header_array)

        # keep track of tables that have been created for each filename group.
        # if a second filename group tries to create a table that's already been
        # used by another filename group, we need to add a unique suffix
        used_table_names = set()
        for unified_header_text, filenames in headers_seen.items():
            # we're going to use these headers to join all the CSVs
            # by index, not by the actual name here.
            unified_headers = unified_header_text.split(JOIN_SEQ)
            # TODO: get a unified filename for all these files to get
            # written to a single database table with
            table_basename = self.table_name_from_filenames(filenames)
            suffix = 0
            table_name = f"{table_basename}{suffix or ''}"
            # pre-increment it in case table_name without a suffix is
            # already a table, then we'll start at 2 not 1 or 0 and we
            # won't need to add a _1 or _0 to every table
            suffix = 1
            while table_name in used_table_names:
                suffix += 1
                table_name = f"{table_basename}{suffix}"
            used_table_names.add(table_name)
            agency_dbname = re.sub(r"[\s\.]+", "_", agency.name.replace("'", ""))
            db_filepath = os.path.join(OUTPUT_DIRECTORY, f"{agency_dbname}.db")
            db = sqlite_utils.Database(sqlite3.connect(db_filepath))
            table = db[table_name]
            for filename in filenames:
                csv = filename_csv_lookup[filename]
                self.write_database(
                    agency, table, csv, unified_headers,
                    filename=filename or "incidents"
                )

        return self.total_rows

    def handle(self, *args, **options):
        # keep track of all headers seen in every file
        self.filename_headers = tablib.Dataset(headers=[
            "Processed Doc Filename", "Header Name"
        ])
        # total number of agencies with completed files
        self.total_agencies = 0
        # total CSV rows seen
        self.total_rows = 0
        # every CSV row goes into here (as dicts)
        self.all_rows = []

        if not os.path.exists(OUTPUT_DIRECTORY):
            os.makedirs(OUTPUT_DIRECTORY)

        # Document.objects.filter(status__in=['complete',
        # 'awaiting-cleaning', 'awaiting-csv', 'awaiting-reading',
        # 'awaiting-extraction', 'supporting-document', 'case-doc',
        # 'unchecked']).count()
        complete_docs = Document.objects.filter(
            status__in=[
                'complete',
                'auto-extracted',
                'case-doc',
            ]
        )
        n_complete_docs  = complete_docs.count()
        print(f"{n_complete_docs} CSVs built from responsive documents")

        agencies = Agency.objects.all()
        for agency in agencies:
            n_rows_processed = self.process_agency(
                agency,
            )
            if n_rows_processed:
                self.total_agencies += 1

        # with open("filename_headers.csv", "w") as f:
        #     f.write(self.filename_headers.csv)

        # json_data = []
        # # tablib Dataset
        # data = None
        # for row in all_rows:
        #     json_data.append(row)
        #     # row here is a fully flattened dict with all extracted values
        #     if data is None:
        #         data = tablib.Dataset(headers=row.keys())
        #     # if we need to add a new column we haven't seen yet, we need to
        #     # re-create the whole dataset with the new row
        #     # this tests if any of row's keys aren't in headers
        #     if set(row.keys()).difference(set(data.headers)):
        #         for h in row.keys():
        #             if h in data.headers:
        #                 continue
        #             data.append_col([None]*len(data), header=h)
        #     # build a properly ordered row consisting of all headers
        #     # in the proper order!
        #     values = []
        #     for h in data.headers:
        #         values.append(row.get(h))
        #     data.append(values)

        # with open(f"all_records.csv", "w") as f:
        #     f.write(data.csv)

        print(f"{self.total_agencies} agencies with completed records")
        print(f"{self.total_rows} total IA records processed")

