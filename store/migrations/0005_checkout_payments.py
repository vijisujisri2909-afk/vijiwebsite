import secrets

from django.db import migrations, models


def populate_order_ids_and_statuses(apps, schema_editor):
    Order = apps.get_model("store", "Order")
    database = schema_editor.connection.alias
    used = set()

    for order in Order.objects.using(database).all().iterator():
        while True:
            candidate = str(secrets.randbelow(900000) + 100000)
            if candidate not in used:
                used.add(candidate)
                break
        order.order_id = candidate
        if order.order_status == "confirmed":
            order.order_status = "placed"
        order.save(update_fields=("order_id", "order_status"))


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_seed_catalog"),
    ]

    operations = [
        migrations.RenameField(
            model_name="order",
            old_name="full_name",
            new_name="customer_name",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="status",
            new_name="order_status",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="total",
            new_name="total_amount",
        ),
        migrations.AddField(
            model_name="order",
            name="city",
            field=models.CharField(default="", max_length=80),
        ),
        migrations.AddField(
            model_name="order",
            name="landmark",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="order",
            name="order_id",
            field=models.CharField(blank=True, max_length=6, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[
                    ("cod", "Cash on delivery"),
                    ("upi", "UPI"),
                    ("razorpay", "Razorpay / card (mock)"),
                ],
                default="cod",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_proof",
            field=models.ImageField(blank=True, upload_to="payment-proofs/"),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[("pending", "Pending"), ("paid", "Paid")],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="pincode",
            field=models.CharField(default="", max_length=10),
        ),
        migrations.AddField(
            model_name="order",
            name="state",
            field=models.CharField(default="Tamil Nadu", max_length=80),
        ),
        migrations.RunPython(populate_order_ids_and_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_id",
            field=models.CharField(editable=False, max_length=6, unique=True),
        ),
        migrations.AlterField(
            model_name="order",
            name="order_status",
            field=models.CharField(
                choices=[
                    ("placed", "Placed"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                ],
                default="placed",
                max_length=20,
            ),
        ),
    ]
