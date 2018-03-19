# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-03-14 07:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0006_device_used_in'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='used_in',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='devices.Device'),
        ),
    ]
