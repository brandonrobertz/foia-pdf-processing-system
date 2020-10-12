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
        ).values('value')
        return JsonResponse(list(fc), safe=False)

    elif request.method == "POST":
        fieldname = request.POST['fieldname']
        value = request.POST['value']
        fc, created = FieldCategory.objects.get_or_create(
            fieldname=fieldname,
            value=value
        )
        return JsonResponse({'status': 'ok'})
