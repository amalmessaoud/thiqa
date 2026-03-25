import cloudinary
import cloudinary.uploader
from app.config import CLOUDINARY_URL


def _init():
    """Initialize Cloudinary from CLOUDINARY_URL env var — called lazily."""
    if CLOUDINARY_URL:
        cloudinary.config(cloudinary_url=CLOUDINARY_URL)


def upload_screenshot(file_path: str, folder: str = "thiqa/reports") -> str:
    """
    Upload a local file to Cloudinary and return the secure URL.

    Args:
        file_path: local path to the image file
        folder: Cloudinary folder to store in

    Returns:
        secure_url (str)

    Raises:
        Exception if upload fails
    """
    _init()
    result = cloudinary.uploader.upload(
        file_path,
        folder=folder,
        resource_type="image",
        overwrite=False,
    )
    return result["secure_url"]