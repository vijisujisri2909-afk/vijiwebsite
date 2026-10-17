from .models import Cart, Category


def shop_navigation(request):
    cart_count = 0
    if request.session.session_key:
        cart = Cart.objects.filter(
            session_key=request.session.session_key
        ).first()
        if cart:
            cart_count = sum(
                cart.items.values_list("quantity", flat=True)
            )
    return {"nav_categories": Category.objects.all(), "cart_count": cart_count}
