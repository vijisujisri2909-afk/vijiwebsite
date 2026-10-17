import re

from django import forms

from .models import Order


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=120, label="Full name")
    phone = forms.CharField(max_length=20, label="Phone number")
    address = forms.CharField(
        max_length=500, widget=forms.Textarea(attrs={"rows": 3}), label="Full address"
    )
    pincode = forms.CharField(max_length=10, label="Pincode")
    city = forms.CharField(max_length=80, label="City")
    state = forms.CharField(max_length=80, initial="Tamil Nadu", label="State")
    landmark = forms.CharField(max_length=120, required=False, label="Landmark")
    payment_method = forms.ChoiceField(choices=Order.PaymentMethod.choices)
    payment_proof = forms.ImageField(required=False, label="UPI payment screenshot")

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        digits = re.sub(r"\D", "", phone)
        if not 10 <= len(digits) <= 15:
            raise forms.ValidationError("Enter a valid phone number.")
        return phone

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pincode):
            raise forms.ValidationError("Enter a valid 6-digit pincode.")
        return pincode

    def clean_payment_proof(self):
        proof = self.cleaned_data.get("payment_proof")
        if proof and proof.size > 5 * 1024 * 1024:
            raise forms.ValidationError("The payment screenshot must be 5 MB or smaller.")
        return proof
