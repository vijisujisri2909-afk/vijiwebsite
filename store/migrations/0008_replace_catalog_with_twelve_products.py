from django.db import migrations, models


CATALOG = (
    (
        "claw-clips",
        (
            (
                "Big Matte Pink Claw Clip",
                149,
                "Pink",
                "A soft matte pink claw clip for an easy everyday updo.",
                "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?q=80&w=500",
            ),
            (
                "Korean Cream Claw",
                199,
                "Cream",
                "A creamy neutral claw clip for a polished everyday style.",
                "https://images.unsplash.com/photo-1596462502278-27bfdc403348?q=80&w=500",
            ),
            (
                "Tortoise Brown Claw",
                179,
                "Brown",
                "A warm tortoise-style claw clip for a classic look.",
                "https://images.pexels.com/photos/20166053/pexels-photo-20166053/free-photo-of-hair-clip-close-up.jpeg?w=500",
            ),
            (
                "Clear Small Claw Set",
                129,
                "Clear",
                "A set of small clear clips for simple everyday styling.",
                "https://images.unsplash.com/photo-1610701596061-2ecf227e85b2?q=80&w=500",
            ),
        ),
    ),
    (
        "scrunchies",
        (
            (
                "Pink Satin Scrunchie",
                79,
                "Pink",
                "A silky pink scrunchie for gentle, comfortable styling.",
                "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?q=80&w=500",
            ),
            (
                "Velvet Red Scrunchie",
                89,
                "Red",
                "A soft red velvet scrunchie with a rich finish.",
                "https://images.unsplash.com/photo-1611085583191-a3b181a88401?q=80&w=500",
            ),
            (
                "Floral Cotton Scrunchie",
                99,
                "Floral",
                "A cheerful floral scrunchie for a pop of pattern.",
                "https://images.pexels.com/photos/30284737/pexels-photo-30284737/free-photo-of-elegant-chiffon-scrunchie-on-designer-bag.jpeg?w=500",
            ),
            (
                "Silk Beige Scrunchie",
                85,
                "Beige",
                "A neutral silk-look scrunchie for a soft everyday style.",
                "https://images.pexels.com/photos/10064224/pexels-photo-10064224.png?w=500",
            ),
        ),
    ),
    (
        "bow-clips",
        (
            (
                "Pearl Bow Clip",
                119,
                "Pearl",
                "A delicate bow clip with a little extra shine.",
                "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?q=80&w=500",
            ),
            (
                "Black Velvet Bow",
                129,
                "Black",
                "A classic dark bow clip for a polished finishing touch.",
                "https://images.pexels.com/photos/14360411/pexels-photo-14360411.jpeg?w=500",
            ),
        ),
    ),
    (
        "mini-clips",
        (
            (
                "Daisy Mini Clip Set",
                149,
                "White",
                "A playful mini clip set for adding a little detail to your hair.",
                "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?q=80&w=500",
            ),
            (
                "Star Mini Clips",
                99,
                "Gold",
                "A set of star-inspired mini clips for an easy finishing touch.",
                "https://images.pexels.com/photos/18421514/pexels-photo-18421514/free-photo-of-hair-clips-on-bed.jpeg?w=500",
            ),
        ),
    ),
)


def replace_catalog(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    database = schema_editor.connection.alias

    for slug, products in CATALOG:
        category = Category.objects.using(database).get(slug=slug)
        used_product_ids = set()

        for index, (name, price, color, description, image_url) in enumerate(products):
            product = (
                Product.objects.using(database)
                .filter(category=category, name=name)
                .exclude(pk__in=used_product_ids)
                .first()
            )
            if product is None:
                product = (
                    Product.objects.using(database)
                    .filter(category=category)
                    .exclude(pk__in=used_product_ids)
                    .order_by("pk")
                    .first()
                )

            values = {
                "name": name,
                "price": price,
                "original_price": price,
                "category": category,
                "image_url": image_url,
                "image": "",
                "color": color,
                "is_trending": index < 2,
                "stock": 50,
                "description": description,
            }
            if product is None:
                product = Product.objects.using(database).create(**values)
            else:
                for field, value in values.items():
                    setattr(product, field, value)
                product.save(using=database, update_fields=tuple(values))
            used_product_ids.add(product.pk)

        Product.objects.using(database).filter(category=category).exclude(
            pk__in=used_product_ids
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0007_product_image_urls_and_real_catalog"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="image_url",
            field=models.URLField(
                blank=True,
                help_text="Use external URL",
                max_length=500,
                null=True,
            ),
        ),
        migrations.RunPython(replace_catalog, migrations.RunPython.noop),
    ]
