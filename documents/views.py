import os
import json
import shutil

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from pdf2image import convert_from_path

from .models import Agency, ProcessedDocument, FieldCategory


def fieldname_values(request):
    if request.method == "GET":
        fieldname = request.GET['fieldname']
        query = request.GET.get('q')
        q_kwargs= dict(
            fieldname=fieldname,
        )
        if query:
            q_kwargs['value__icontains'] = query
        fc = FieldCategory.objects.filter(
            **q_kwargs
        ).order_by("-count").values('value')
        return JsonResponse(list(fc), safe=False)

    elif request.method == "POST":
        fieldname = request.POST['fieldname']
        value = request.POST['value']
        fc, created = FieldCategory.objects.get_or_create(
            fieldname=fieldname,
            value=value
        )
        return JsonResponse({'status': 'ok'})


def fieldname_value_count(request):
    # just let it explode if people don't POST properly
    fieldname = request.POST['fieldname']
    value = request.POST['value']
    fc = FieldCategory.objects.get(
        fieldname=fieldname,
        value=value
    )
    fc.count += 1
    fc.save()
    return JsonResponse({'status': 'ok'})


SEGMENTABLE_STATUSES = [
    "awaiting-reading",
    "auto-extracted",
    "awaiting-extraction",
    "case-doc",
    "unchecked",
]


def agency_segmentable_pdocs(agency):
    return ProcessedDocument.objects.filter(
        file__endswith=".ocr.pdf",
        document__agency=agency,
        document__status__in=SEGMENTABLE_STATUSES,
        pages__gt=0,
    ).order_by("-pages")


def agency_pdoc_images(agency, pdoc):
    if not pdoc.file:
        return []
    if not pdoc.file.path or not os.path.exists(pdoc.file.path):
        return []

    print(f"Parsing: {pdoc}")

    pages = convert_from_path(pdoc.file.path, dpi=200)

    page_count = len(pages)
    if not page_count:
        return []

    media_path = "wapd-segment-temp"
    tmpdir = os.path.join(settings.MEDIA_ROOT, media_path)

    # clear it (delete all files)
    # TODO: store these by filename, reuse them and allow
    # multi-processing LOL
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)

    os.makedirs(tmpdir)

    img_files = []
    total_pages = 0
    for idx, page in enumerate(pages):
        filename = f"page-{idx}.jpg"
        tmpfile_path = os.path.join(
            tmpdir, filename
        )
        page.save(tmpfile_path, "JPEG")
        url = os.path.join(settings.MEDIA_URL, media_path, filename)
        img_files.append(url)

    print(f" - Pages: {len(img_files)}")
    return img_files


def GET_segmentable_home(request):
    agencies = Agency.objects.filter(
        document__processeddocument__file__endswith=".ocr.pdf",
        document__processeddocument__status__in=SEGMENTABLE_STATUSES,
    ).distinct()

    total_segmentable_pdocs = 0
    segmented_pdocs = 0
    unsegmented_pdocs = 0
    for agency in agencies:
        segmentable_pdocs = agency_segmentable_pdocs(agency)
        agency.total_segmentable_pdocs = segmentable_pdocs.count()
        agency.segmented_pdocs = segmentable_pdocs.filter(
            incident_pgs__isnull=False,
            incident_pgs__len__gt=0
        ).count()
        agency.unsegmented_pdocs = segmentable_pdocs.exclude(
            incident_pgs__isnull=False,
            incident_pgs__len__gt=0
        ).count()
        total_segmentable_pdocs += agency.total_segmentable_pdocs
        segmented_pdocs += agency.segmented_pdocs
        unsegmented_pdocs += agency.unsegmented_pdocs

    context = {
        "agencies": agencies,
        "total_segmentable_pdocs": total_segmentable_pdocs,
        "segmented_pdocs": segmented_pdocs,
        "unsegmented_pdocs": unsegmented_pdocs,
    }
    return render(request, "segmentable_home.htmx", context=context)


def GET_agency(request, id):
    agency = Agency.objects.get(pk=id)
    context = {
        "status": "ok",
        "agency": agency,
    }
    return render(request, "agency.htmx", context=context)


def GET_pdocs(request, agency_id):
    agency = Agency.objects.get(pk=agency_id)
    pdocs = agency_segmentable_pdocs(agency)
    context = {
        "status": "ok",
        "agency": agency,
        "pdocs": pdocs,
    }
    return render(request, "pdocs.htmx", context=context)


def GET_pdoc(request, pdoc_id):
    pdoc = ProcessedDocument.objects.get(pk=pdoc_id)
    context = {
        "status": "ok",
        "pdoc": pdoc,
    }
    return render(request, "pdoc.htmx", context=context)


def GET_pdoc_image_segments(request, pdoc_id):
    pdoc = ProcessedDocument.objects.get(pk=pdoc_id)
    context = {
        "status": "ok",
        "pdoc": pdoc,
        "agency": pdoc.document.agency,
        "images": pdoc.images(),
    }
    return render(request, "pdoc_image_segments.htmx", context=context)


def POST_save_image_segments(request, pdoc_id):
    pdoc = ProcessedDocument.objects.get(pk=pdoc_id)
    print("POST", request.POST)
    incident_pgs = json.loads(request.POST['incident_pgs'])
    print("incident_pgs", incident_pgs)
    pdoc.incident_pgs = incident_pgs
    pdoc.save()
    context = {
        "status": "ok",
        "pdoc_id": pdoc.pk,
        "incident_pgs": incident_pgs,
    }
    return JsonResponse(context)


def segment_cases_list(request):
    pass


def segments_and_images_for_agency(request):
    pass


def save_pdoc_segments(request):
    pass
