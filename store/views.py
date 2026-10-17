import hashlib
import hmac
import json
import base64
import logging
from urllib.parse import quote
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
import qrcode
import qrcode.image.svg

from .forms import CheckoutForm
from .models import Cart, CartItem, Category, Order, OrderItem, Product, generate_order_id

DELIVERY_CHARGE = 40
UPI_ID = "clippap@okaxis"
logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    pass


def _create_razorpay_order(receipt, amount):
    credentials = f"{settings.RAZORPAY_KEY_ID}:{settings.RAZORPAY_KEY_SECRET}"
    authorization = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
    payload = json.dumps(
        {"amount": amount * 100, "currency": "INR", "receipt": receipt}
    ).encode("utf-8")
    request = Request(
        "https://api.razorpay.com/v1/orders",
        data=payload,
        headers={
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        logger.exception("Razorpay order creation failed with HTTP %s.", exc.code)
        raise PaymentGatewayError("Razorpay could not start the payment. Please try again.") from exc
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.exception("Could not create a Razorpay order.")
        raise PaymentGatewayError("Razorpay is unavailable right now. Please try again.") from exc
    gateway_order_id = result.get("id") if isinstance(result, dict) else None
    if not isinstance(gateway_order_id, str) or not gateway_order_id.startswith("order_"):
        logger.error("Razorpay returned an invalid order response.")
        raise PaymentGatewayError("Razorpay returned an invalid response. Please try again.")
    return gateway_order_id


def _cart_for(request, create=False):
    session_key = request.session.session_key
    if not session_key and create:
        request.session.create()
        session_key = request.session.session_key
    if not session_key:
        return None
    cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart


def _return_to(request):
    destination = request.POST.get("next", "")
    if url_has_allowed_host_and_scheme(
        destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(destination)
    return redirect("home")


def home(request):
    products = Product.objects.select_related("category").all()
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(name__icontains=query) | products.filter(
            description__icontains=query
        )
    categories = Category.objects.prefetch_related("products").all()
    trending_by_category = [
        (category, category.products.filter(is_trending=True)[:2])
        for category in categories
    ]
    return render(
        request,
        "store/home.html",
        {
            "products": products,
            "categories": categories,
            "trending_by_category": trending_by_category,
            "search_query": query,
        },
    )


def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.select_related("category").all()
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(name__icontains=query) | products.filter(
            description__icontains=query
        )
    return render(
        request,
        "store/category.html",
        {
            "category": category,
            "active_category": category,
            "products": products,
            "category_featured_product": products.first(),
            "categories": Category.objects.all(),
            "search_query": query,
        },
    )


def cart_view(request):
    cart = _cart_for(request)
    items = cart.items.select_related("product", "product__category") if cart else []
    subtotal = sum(item.line_total for item in items)
    return render(
        request,
        "store/cart.html",
        {
            "cart_items": items,
            "cart_subtotal": subtotal,
            "delivery_charge": DELIVERY_CHARGE if items else 0,
            "cart_total": subtotal + (DELIVERY_CHARGE if items else 0),
            "categories": Category.objects.all(),
        },
    )


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if product.stock < 1:
        messages.error(request, "This lovely find is currently out of stock.")
        return _return_to(request)
    cart = _cart_for(request, create=True)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if item.quantity >= product.stock:
            messages.error(request, "You’ve reached the available stock for this item.")
            return _return_to(request)
        item.quantity += 1
        item.save(update_fields=("quantity",))
    messages.success(request, f"{product.name} added to your bag.")
    return _return_to(request)


@require_POST
def update_cart_item(request, item_id):
    cart = _cart_for(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    try:
        quantity = int(request.POST.get("quantity", ""))
    except ValueError:
        messages.error(request, "Please enter a valid quantity.")
        return redirect("cart")
    if quantity < 1:
        item.delete()
    elif quantity > item.product.stock:
        messages.error(request, "The requested quantity is not available.")
    else:
        item.quantity = quantity
        item.save(update_fields=("quantity",))
    return redirect("cart")


@require_POST
def remove_cart_item(request, item_id):
    cart = _cart_for(request)
    get_object_or_404(CartItem, pk=item_id, cart=cart).delete()
    messages.success(request, "Item removed from your bag.")
    return redirect("cart")


def _upi_qr_data_uri(total, order_note="CLIPPAP checkout"):
    payment_uri = "upi://pay?" + urlencode(
        {
            "pa": UPI_ID,
            "pn": "Viji's Clip Pap",
            "am": f"{total:.2f}",
            "cu": "INR",
            "tn": order_note,
        }
    )
    image = qrcode.make(payment_uri, image_factory=qrcode.image.svg.SvgPathImage)
    encoded = base64.b64encode(image.to_string()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _checkout_context(cart_items, form=None):
    subtotal = sum(item.line_total for item in cart_items)
    return {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "delivery_charge": DELIVERY_CHARGE,
        "total": subtotal + DELIVERY_CHARGE,
        "upi_id": UPI_ID,
        "upi_qr_data_uri": _upi_qr_data_uri(subtotal + DELIVERY_CHARGE),
        "razorpay_enabled": bool(
            settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET
        ),
        "form": form or CheckoutForm(),
        "categories": Category.objects.all(),
    }


def checkout(request):
    cart = _cart_for(request)
    items = list(cart.items.select_related("product", "product__category") if cart else [])
    if not items:
        messages.info(request, "Your bag is empty. Find something cute first!")
        return redirect("cart")
    return render(request, "store/checkout.html", _checkout_context(items))


@require_POST
def place_order(request):
    cart = _cart_for(request)
    cart_items = list(
        cart.items.select_related("product", "product__category") if cart else []
    )
    if not cart_items:
        messages.info(request, "Your bag is empty. Find something cute first!")
        return redirect("cart")

    form = CheckoutForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(
            request,
            "store/checkout.html",
            _checkout_context(cart_items, form),
        )

    with transaction.atomic():
        for item in cart_items:
            product = Product.objects.select_for_update().get(pk=item.product_id)
            if item.quantity > product.stock:
                messages.error(
                    request,
                    f"Only {product.stock} of {product.name} are available. Please update your bag.",
                )
                return redirect("cart")

        subtotal = sum(item.line_total for item in cart_items)
        total = subtotal + DELIVERY_CHARGE
        data = form.cleaned_data
        payment_method = data["payment_method"]
        order_id = generate_order_id()
        gateway_order_id = ""
        if (
            payment_method == Order.PaymentMethod.RAZORPAY
            and settings.RAZORPAY_KEY_ID
            and settings.RAZORPAY_KEY_SECRET
        ):
            try:
                gateway_order_id = _create_razorpay_order(order_id, total)
            except PaymentGatewayError as exc:
                messages.error(request, str(exc))
                return render(
                    request,
                    "store/checkout.html",
                    _checkout_context(cart_items, form),
                )
        order = Order.objects.create(
            order_id=order_id,
            user=request.user if request.user.is_authenticated else None,
            customer_name=data["full_name"],
            phone=data["phone"],
            address=data["address"],
            pincode=data["pincode"],
            city=data["city"],
            state=data["state"],
            landmark=data["landmark"],
            payment_method=payment_method,
            payment_status=Order.PaymentStatus.PENDING,
            total_amount=total,
            payment_proof=data.get("payment_proof"),
            gateway_order_id=gateway_order_id,
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    unit_price=item.product.price,
                    quantity=item.quantity,
                )
                for item in cart_items
            ]
        )
        for item in cart_items:
            product = Product.objects.get(pk=item.product_id)
            product.stock -= item.quantity
            product.save(update_fields=("stock",))
        cart.items.all().delete()

    order_ids = request.session.get("clippap_order_ids", [])
    request.session["clippap_order_ids"] = (order_ids + [order.order_id])[-20:]
    return redirect("order_success", order_id=order.order_id)


def order_success(request, order_id):
    if order_id not in request.session.get("clippap_order_ids", []):
        raise Http404("Order not found.")
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_id=order_id)
    whatsapp_url = "https://wa.me/?text=" + quote(
        f"Hi, my order ID is {order.order_id}. Total: Rs. {order.total_amount}."
    )
    return render(
        request,
        "store/order_success.html",
        {
            "order": order,
            "whatsapp_url": whatsapp_url,
            "categories": Category.objects.all(),
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "razorpay_amount": order.total_amount * 100,
        },
    )


@require_POST
def complete_mock_payment(request, order_id):
    if order_id not in request.session.get("clippap_order_ids", []):
        raise Http404("Order not found.")
    order = get_object_or_404(Order, order_id=order_id)
    if (
        order.payment_method != Order.PaymentMethod.RAZORPAY
        or order.gateway_order_id
        or (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
    ):
        messages.error(request, "This order is not awaiting a mock card payment.")
        return redirect("order_success", order_id=order_id)
    order.payment_status = Order.PaymentStatus.PAID
    order.save(update_fields=("payment_status",))
    messages.success(request, "Demo payment marked as successful.")
    return redirect("order_success", order_id=order_id)


@require_POST
def verify_razorpay_payment(request, order_id):
    if order_id not in request.session.get("clippap_order_ids", []):
        raise Http404("Order not found.")
    order = get_object_or_404(Order, order_id=order_id)
    submitted_order_id = request.POST.get("razorpay_order_id", "")
    payment_id = request.POST.get("razorpay_payment_id", "")
    signature = request.POST.get("razorpay_signature", "")
    if (
        order.payment_method != Order.PaymentMethod.RAZORPAY
        or not order.gateway_order_id
        or submitted_order_id != order.gateway_order_id
        or not payment_id
        or not signature
    ):
        messages.error(request, "Could not verify the payment. Please contact us.")
        return redirect("order_success", order_id=order_id)

    signed_payload = f"{order.gateway_order_id}|{payment_id}".encode("utf-8")
    expected_signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        messages.error(request, "Payment verification failed. Please contact us.")
        logger.warning("Invalid Razorpay signature for order %s.", order.order_id)
        return redirect("order_success", order_id=order_id)

    order.payment_status = Order.PaymentStatus.PAID
    order.save(update_fields=("payment_status",))
    messages.success(request, "Razorpay payment verified successfully.")
    return redirect("order_success", order_id=order_id)
