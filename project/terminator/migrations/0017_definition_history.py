# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-05-30 13:08
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('terminator', '0016_rename_allows_administrative_status_reason'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalDefinition',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('text', models.TextField(verbose_name='definition text')),
                ('is_finalized', models.BooleanField(default=False, verbose_name='is finalized')),
                ('source', models.URLField(blank=True, verbose_name='source')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
                'verbose_name': 'historical definition',
            },
        ),
        migrations.AddField(
            model_name='historicaldefinition',
            name='concept',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='terminator.Concept'),
        ),
        migrations.AddField(
            model_name='historicaldefinition',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaldefinition',
            name='language',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='terminator.Language'),
        ),
    ]
