# Generated by Django 5.0.6 on 2025-07-05 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0004_paymenttransaction_paystackevent_order_currency_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=255, unique=True),
        ),
    ]
