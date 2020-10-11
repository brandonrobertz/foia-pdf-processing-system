# Generated by Django 3.1.2 on 2020-10-10 21:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_auto_20201009_0138'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='agency',
            options={'ordering': ('name',)},
        ),
        migrations.AlterModelOptions(
            name='document',
            options={'ordering': ('file',)},
        ),
        migrations.AlterModelOptions(
            name='processeddocument',
            options={'ordering': ('file',)},
        ),
        migrations.RemoveConstraint(
            model_name='processeddocument',
            name='unique-processed-agency-file',
        ),
    ]