# -*- coding: utf-8 -*-
# Generated by Django 1.11.22 on 2019-10-10 18:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paying_for_college', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='school',
            name='cohort_rank_degrees',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
