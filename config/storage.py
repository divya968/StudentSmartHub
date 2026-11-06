import os
import uuid
from io import BytesIO
from urllib.request import urlopen

import cloudinary.uploader
from cloudinary.utils import cloudinary_url

from django.core.files import File
from django.core.files.storage import Storage


class CloudinaryRawStorage(Storage):

    def get_available_name(self, name, max_length=None):
        return name

    def _save(self, name, content):
        extension = os.path.splitext(name)[1].lower()
        public_id = f"student_smart_hub/{uuid.uuid4().hex}{extension}"

        content.seek(0)

        result = cloudinary.uploader.upload(
            content,
            resource_type="raw",
            public_id=public_id,
            overwrite=False,
        )

        return result["public_id"]

    def url(self, name):
        url, _ = cloudinary_url(
            name,
            resource_type="raw",
            secure=True,
        )
        return url

    def _open(self, name, mode="rb"):
        url = self.url(name)

        with urlopen(url, timeout=30) as response:
            file_content = BytesIO(response.read())

        return File(file_content, name=os.path.basename(name))

    def exists(self, name):
        return False

    def delete(self, name):
        cloudinary.uploader.destroy(
            name,
            resource_type="raw",
            invalidate=True,
        )