# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2017-10-27 19:20
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('terminator', '0009_rename_word_to_term'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='concept',
            options={'ordering': ['id'], 'verbose_name': 'concept', 'verbose_name_plural': 'concepts'},
        ),
    ]
