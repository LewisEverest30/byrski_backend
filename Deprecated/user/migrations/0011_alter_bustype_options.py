# Generated by Django 4.2 on 2024-02-06 11:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0010_alter_bustype_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bustype',
            options={'verbose_name': '大巴车类型(只支持两种类型)', 'verbose_name_plural': '大巴车类型(只支持两种类型)'},
        ),
    ]
