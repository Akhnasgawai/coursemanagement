# Generated by Django 4.2.3 on 2023-07-25 11:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("course", "0006_subscribedcourse_is_paid_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscribedcourse",
            name="subscribed_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]