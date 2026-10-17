from django.test import TestCase
from django.urls import reverse
import hashlib
import hmac
import io
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from .models import Cart, Category, Order, Product


class CatalogTests(TestCase):
    def test_seeded_catalog_has_twelve_products_and_distinct_category_photos(self):
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(Product.objects.count(), 12)
        expected_counts = {
            "claw-clips": 4,
            "scrunchies": 4,
            "bow-clips": 2,
            "mini-clips": 2,
        }
        self.assertEqual(
            list(
                Category.objects.values_list("slug", flat=True)
            ),
            ["claw-clips", "scrunchies", "bow-clips", "mini-clips"],
        )
        for slug, count in expected_counts.items():
            products = Product.objects.filter(category__slug=slug)
            self.assertEqual(products.count(), count)
            image_urls = list(products.values_list("image_url", flat=True))
            self.assertTrue(all(image_urls))
            self.assertEqual(len(set(image_urls)), count)

    def test_home_and_category_pages_render_product_photos(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your hair deserves")
        self.assertContains(response, "Big Matte Pink Claw Clip")
        self.assertContains(
            response,
            "https://images.pexels.com/photos/20166056/pexels-photo-20166056/",
        )
        html = response.content.decode()
        desktop_nav = html.split('aria-label="Shop categories">', 1)[1].split(
            "</nav>", 1
        )[0]
        mobile_nav = html.split('aria-label="Mobile shop categories">', 1)[1].split(
            "</nav>", 1
        )[0]
        for category in Category.objects.all():
            image_url = f"/static/store/images/{category.slug}.svg"
            category_url = reverse("category", kwargs={"slug": category.slug})
            self.assertIn(category_url, desktop_nav)
            self.assertIn(image_url, desktop_nav)
            self.assertIn(category_url, mobile_nav)
            self.assertIn(image_url, mobile_nav)

        response = self.client.get(
            reverse("category", kwargs={"slug": "scrunchies"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pink Satin Scrunchie")
        self.assertContains(response, response.context["category_featured_product"].image_url)
        self.assertContains(
            response,
            "category-link flex items-center gap-1.5 py-7 text-[11px] tracking-[.12em] font-bold active",
        )
        self.assertEqual(response.context["products"].count(), 4)
        for product in response.context["products"]:
            self.assertContains(response, product.image_url.replace("&", "&amp;"))

    def test_claw_clip_products_render_four_distinct_real_photo_urls(self):
        response = self.client.get(
            reverse("category", kwargs={"slug": "claw-clips"})
        )
        products = response.context["products"]
        image_urls = [product.image_url for product in products]

        self.assertEqual(len(image_urls), 4)
        self.assertEqual(len(set(image_urls)), 4)
        for image_url in image_urls:
            self.assertContains(response, image_url.replace("&", "&amp;"))
        self.assertFalse(
            any("/static/store/images/" in image_url for image_url in image_urls)
        )

    def test_search_filters_catalog(self):
        response = self.client.get(reverse("home"), {"q": "Daisy"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["products"].values_list("name", flat=True)),
            ["Daisy Mini Clip Set"],
        )


class ShoppingFlowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.get(name="Big Matte Pink Claw Clip")

    def test_add_to_cart_increments_badge_and_cart_quantity(self):
        response = self.client.post(
            reverse("add_to_cart", args=(self.product.pk,)),
            {"next": reverse("home")},
        )
        self.assertRedirects(response, reverse("home"))
        cart = Cart.objects.get()
        self.assertEqual(cart.items.get(product=self.product).quantity, 1)

        self.client.post(
            reverse("add_to_cart", args=(self.product.pk,)),
            {"next": reverse("home")},
        )
        response = self.client.get(reverse("cart"))
        self.assertContains(response, "Rs. 298")
        self.assertEqual(response.context["cart_count"], 2)

    def test_checkout_creates_order_decrements_stock_and_clears_cart(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        original_stock = self.product.stock
        response = self.client.post(
            reverse("place_order"),
            {
                "full_name": "Asha",
                "phone": "9876543210",
                "address": "12 Rose Lane",
                "pincode": "600001",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "payment_method": "cod",
            },
        )
        order = Order.objects.get()
        self.assertRedirects(
            response, reverse("order_success", args=(order.order_id,))
        )
        response = self.client.get(reverse("order_success", args=(order.order_id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order placed successfully!")
        self.assertContains(response, f"wa.me/?text=Hi%2C%20my%20order%20ID%20is%20{order.order_id}")

        self.assertEqual(order.total_amount, self.product.price + 40)
        self.assertEqual(order.items.get().product_name, self.product.name)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, original_stock - 1)
        self.assertFalse(order.user_id)
        self.assertEqual(Cart.objects.get().items.count(), 0)

    def test_checkout_requires_contact_and_delivery_details(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        response = self.client.post(
            reverse("place_order"),
            {
                "full_name": "",
                "phone": "",
                "address": "",
                "pincode": "",
                "city": "",
                "state": "",
                "payment_method": "cod",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertIn("full_name", response.context["form"].errors)
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_shows_delivery_and_payment_options(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        response = self.client.get(reverse("checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UPI")
        self.assertContains(response, "clippap@okaxis")
        self.assertContains(response, "Cash on delivery")
        self.assertContains(response, "Rs. 40")
        self.assertContains(response, "name=\"pincode\"")
        self.assertTrue(response.context["upi_qr_data_uri"].startswith("data:image/svg+xml;base64,"))

    def test_upi_order_saves_uploaded_proof_and_stays_pending(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        image = io.BytesIO()
        Image.new("RGB", (2, 2), color="pink").save(image, format="PNG")
        with tempfile.TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root
        ):
            response = self.client.post(
                reverse("place_order"),
                {
                    "full_name": "Asha",
                    "phone": "9876543210",
                    "address": "12 Rose Lane",
                    "pincode": "600001",
                    "city": "Chennai",
                    "state": "Tamil Nadu",
                    "landmark": "Near the park",
                    "payment_method": "upi",
                    "payment_proof": SimpleUploadedFile(
                        "proof.png", image.getvalue(), content_type="image/png"
                    ),
                },
            )
            order = Order.objects.get()
            self.assertRedirects(
                response, reverse("order_success", args=(order.order_id,))
            )
            self.assertEqual(order.payment_method, Order.PaymentMethod.UPI)
            self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)
            self.assertTrue(order.payment_proof.name.startswith("payment-proofs/"))

    def test_mock_card_payment_marks_order_paid(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        self.client.post(
            reverse("place_order"),
            {
                "full_name": "Asha",
                "phone": "9876543210",
                "address": "12 Rose Lane",
                "pincode": "600001",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "payment_method": "razorpay",
            },
        )
        order = Order.objects.get()
        response = self.client.post(reverse("mock_payment", args=(order.order_id,)))
        self.assertRedirects(
            response, reverse("order_success", args=(order.order_id,))
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

    def test_razorpay_payment_requires_a_valid_signature(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        self.client.post(
            reverse("place_order"),
            {
                "full_name": "Asha",
                "phone": "9876543210",
                "address": "12 Rose Lane",
                "pincode": "600001",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "payment_method": "razorpay",
            },
        )
        order = Order.objects.get()
        order.gateway_order_id = "order_demo_123"
        order.save(update_fields=("gateway_order_id",))
        payment_id = "pay_demo_123"
        signature = hmac.new(
            b"test-secret",
            f"{order.gateway_order_id}|{payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()

        with override_settings(RAZORPAY_KEY_SECRET="test-secret"):
            response = self.client.post(
                reverse("verify_payment", args=(order.order_id,)),
                {
                    "razorpay_order_id": order.gateway_order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                },
            )

        self.assertRedirects(
            response, reverse("order_success", args=(order.order_id,))
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

    def test_configured_razorpay_order_renders_checkout_popup(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        self.client.post(
            reverse("place_order"),
            {
                "full_name": "Asha",
                "phone": "9876543210",
                "address": "12 Rose Lane",
                "pincode": "600001",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "payment_method": "razorpay",
            },
        )
        order = Order.objects.get()
        order.gateway_order_id = "order_demo_789"
        order.save(update_fields=("gateway_order_id",))

        with override_settings(RAZORPAY_KEY_ID="rzp_test_example"):
            response = self.client.get(
                reverse("order_success", args=(order.order_id,))
            )
            mock_response = self.client.post(
                reverse("mock_payment", args=(order.order_id,))
            )

        self.assertContains(response, "https://checkout.razorpay.com/v1/checkout.js")
        self.assertContains(response, "rzp_test_example")
        self.assertContains(response, "18900")
        self.assertContains(response, "order_demo_789")
        self.assertRedirects(
            mock_response, reverse("order_success", args=(order.order_id,))
        )
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    def test_invalid_razorpay_signature_does_not_mark_order_paid(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        self.client.post(
            reverse("place_order"),
            {
                "full_name": "Asha",
                "phone": "9876543210",
                "address": "12 Rose Lane",
                "pincode": "600001",
                "city": "Chennai",
                "state": "Tamil Nadu",
                "payment_method": "razorpay",
            },
        )
        order = Order.objects.get()
        order.gateway_order_id = "order_demo_456"
        order.save(update_fields=("gateway_order_id",))

        with override_settings(RAZORPAY_KEY_SECRET="test-secret"):
            self.client.post(
                reverse("verify_payment", args=(order.order_id,)),
                {
                    "razorpay_order_id": order.gateway_order_id,
                    "razorpay_payment_id": "pay_demo_456",
                    "razorpay_signature": "invalid",
                },
            )

        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PENDING)

    def test_order_success_is_only_available_in_the_ordering_session(self):
        response = self.client.get(reverse("order_success", args=("123456",)))
        self.assertEqual(response.status_code, 404)

    def test_add_to_cart_rejects_out_of_stock_product(self):
        self.product.stock = 0
        self.product.save(update_fields=("stock",))
        response = self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(Cart.objects.exists())

    def test_cart_quantity_can_be_updated_and_item_removed(self):
        self.client.post(reverse("add_to_cart", args=(self.product.pk,)))
        item = Cart.objects.get().items.get()
        response = self.client.post(
            reverse("update_cart_item", args=(item.pk,)), {"quantity": "3"}
        )
        self.assertRedirects(response, reverse("cart"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        response = self.client.post(
            reverse("remove_cart_item", args=(item.pk,))
        )
        self.assertRedirects(response, reverse("cart"))
        self.assertFalse(Cart.objects.get().items.exists())
