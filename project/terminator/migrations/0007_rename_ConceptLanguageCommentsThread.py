# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def rename_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    perms = Permission.objects.filter(codename__endswith="_conceptlanguagecommentsthread")
    for perm in perms:
        perm.codename = perm.codename.replace('_conceptlanguagecommentsthread', '_conceptinlanguage')
        perm.name = perm.name.replace('concept language comments thread', 'concept in language')
        perm.save(update_fields={'codename', 'name'})


class Migration(migrations.Migration):

    dependencies = [
        ('terminator', '0006_update_repr_cache'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ConceptLanguageCommentsThread',
            new_name='ConceptInLanguage',
        ),
        migrations.RunPython(rename_permissions),
    ]
