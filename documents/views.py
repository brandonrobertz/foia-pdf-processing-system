from django.shortcuts import render
from django.http import JsonResponse

from .models import FieldCategory


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
