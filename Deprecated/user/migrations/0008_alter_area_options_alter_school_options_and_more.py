# Generated by Django 4.2 on 2024-02-05 05:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_alter_user_school'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='area',
            options={'verbose_name': '地区', 'verbose_name_plural': '地区'},
        ),
        migrations.AlterModelOptions(
            name='school',
            options={'verbose_name': '学校(校区)', 'verbose_name_plural': '学校(校区)'},
        ),
        migrations.AlterModelOptions(
            name='user',
            options={'verbose_name': '用户', 'verbose_name_plural': '用户'},
        ),
    ]
