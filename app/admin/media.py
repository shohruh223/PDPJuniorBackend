import os

from django import forms
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string


def get_file_ext(uploaded_file, default_ext=""):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    return ext or default_ext


def save_uploaded_file(uploaded_file, folder):
    ext = get_file_ext(uploaded_file)
    filename = f"{get_random_string(16)}{ext}"
    path = f"{folder}/{filename}"

    return default_storage.save(path, uploaded_file)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        attrs = attrs or {}
        attrs["multiple"] = True
        super().__init__(attrs)


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []

        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]

        return [single_file_clean(data, initial)]