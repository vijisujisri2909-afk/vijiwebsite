from django.db import migrations, models


CATALOG = (
    (
        "claw-clips",
        "Claw Clips",
        (
            (
                "Matte Pink Big Claw",
                149,
                "Pink",
                "A pretty everyday claw clip with a soft matte finish.",
                "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=500",
            ),
            (
                "Cream Korean Claw",
                199,
                "Cream",
                "A creamy neutral claw clip for an easy, polished updo.",
                "https://images.pexels.com/photos/20166053/pexels-photo-20166053/free-photo-of-hair-clip-close-up.jpeg?w=500",
            ),
            (
                "Brown Tortise Claw",
                179,
                "Brown",
                "A warm brown claw clip for everyday hairstyles.",
                "https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=500",
            ),
            (
                "Glossy White Claw",
                129,
                "White",
                "A glossy white clip that pairs with any look.",
                "https://images.pexels.com/photos/20166054/pexels-photo-20166054/free-photo-of-hair-clip-on-towel.jpeg?w=500",
            ),
        ),
    ),
    (
        "scrunchies",
        "Scrunchies",
        (
            (
                "Pink Satin Scrunchie",
                79,
                "Pink",
                "A silky pink scrunchie for gentle, comfortable styling.",
                "https://images.unsplash.com/photo-1585487000160-6ebcfceb0d03?w=500",
            ),
            (
                "Velvet Red Scrunchie",
                89,
                "Red",
                "A soft red velvet scrunchie with a rich finish.",
                "https://images.unsplash.com/photo-1611085583191-a3b181a88401?w=500",
            ),
            (
                "Floral Cotton Scrunchie",
                99,
                "Floral",
                "A cheerful floral scrunchie for a pop of pattern.",
                "https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=500",
            ),
            (
                "Beige Silk Scrunchie",
                85,
                "Beige",
                "A neutral silk-look scrunchie for a soft everyday style.",
                "https://images.pexels.com/photos/6983530/pexels-photo-6983530.jpeg?w=500",
            ),
        ),
    ),
    (
        "bow-clips",
        "Bow Clips",
        (
            (
                "Pearl Bow Clip",
                119,
                "Pearl",
                "A delicate bow clip with a little extra shine.",
                "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=500",
            ),
            (
                "Pink Satin Bow",
                99,
                "Pink",
                "A pink ribbon bow to dress up a ponytail or half-up style.",
                "https://images.pexels.com/photos/14360411/pexels-photo-14360411.jpeg?w=500",
            ),
            (
                "Black Velvet Bow",
                129,
                "Black",
                "A classic black bow with a soft velvet look.",
                "https://images.unsplash.com/photo-1582791694770-cbdc9dda338f?w=500",
            ),
            (
                "White Organza Bow",
                89,
                "White",
                "A light white bow for a sweet finishing touch.",
                "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=500",
            ),
        ),
    ),
    (
        "mini-clips",
        "Mini Clips",
        (
            (
                "Daisy Mini Set 5pcs",
                149,
                "White",
                "A set of five tiny daisy clips for playful hairstyles.",
                "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?w=500",
            ),
            (
                "Heart Mini Clips",
                99,
                "Pink",
                "Tiny clips to add a sweet detail to your hairstyle.",
                "https://images.pexels.com/photos/20166056/pexels-photo-20166056/free-photo-of-hair-clips-on-white-background.jpeg?w=500",
            ),
            (
                "Pearl Mini Clips",
                129,
                "Pearl",
                "Small pearl clips for a subtle touch of shine.",
                "https://images.unsplash.com/photo-1610701596061-2ecf227e85b2?w=500",
            ),
            (
                "Star Mini Clips",
                119,
                "Gold",
                "A playful set of star-inspired mini hair clips.",
                "https://images.pexels.com/photos/18421514/pexels-photo-18421514/free-photo-of-hair-clips-on-bed.jpeg?w=500",
            ),
        ),
    ),
)


def replace_catalog(apps, schema_editor):
    Category = apps.get_model("store", "Category")
    Product = apps.get_model("store", "Product")
    database = schema_editor.connection.alias

    for slug, category_name, products in CATALOG:
        category, _created = Category.objects.using(database).get_or_create(
            slug=slug, defaults={"name": category_name}
        )
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
                product.save(
                    using=database,
                    update_fields=tuple(values),
                )
            used_product_ids.add(product.pk)

        Product.objects.using(database).filter(category=category).exclude(
            pk__in=used_product_ids
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0006_order_gateway_order_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image_url",
            field=models.URLField(
                blank=True,
                help_text="Use external URL",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="products/",
            ),
        ),
        migrations.RunPython(replace_catalog, migrations.RunPython.noop),
    ]
