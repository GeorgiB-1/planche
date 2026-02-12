"""
Cloudflare R2 storage client for Planche.bg.

Handles image upload, download, conversion (WebP), resizing,
and batch product-image ingestion via R2-compatible S3 API.
"""

import boto3
from botocore.config import Config
import os
import io
import concurrent.futures
import time

from PIL import Image
import httpx

from src.config import (
    CF_ACCOUNT_ID,
    R2_ACCESS_KEY,
    R2_SECRET_KEY,
    R2_BUCKET,
    R2_PUBLIC_URL,
)

# ---------------------------------------------------------------------------
# Boto3 S3 client configured for Cloudflare R2
# ---------------------------------------------------------------------------
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def convert_to_webp(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Open *image_bytes* with Pillow, resize so the longest side is at most
    *max_size* (maintaining aspect ratio), and return WebP-encoded bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")

        # Resize so longest side <= max_size, preserving aspect ratio
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=85)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[r2_client] convert_to_webp error: {e}")
        raise


def resize_for_prompt(image_bytes: bytes, max_size: int = 512) -> bytes:
    """Resize an image for a Gemini prompt.

    Keeps the original format (no WebP conversion) -- just scales down so the
    longest side is at most *max_size*.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_format = img.format or "PNG"

        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format=original_format)
        buf.seek(0)
        return buf.read()
    except Exception as e:
        print(f"[r2_client] resize_for_prompt error: {e}")
        raise


# ---------------------------------------------------------------------------
# R2 CRUD operations
# ---------------------------------------------------------------------------

def upload_image(image_bytes: bytes, r2_key: str, content_type: str = "image/webp") -> str:
    """Upload *image_bytes* to R2 under *r2_key* and return the public URL."""
    try:
        s3.put_object(
            Bucket=R2_BUCKET,
            Key=r2_key,
            Body=image_bytes,
            ContentType=content_type,
        )
        return get_image_url(r2_key)
    except Exception as e:
        print(f"[r2_client] upload_image error for key '{r2_key}': {e}")
        raise


def get_image_url(r2_key: str) -> str:
    """Return the public URL for an R2 object."""
    return f"{R2_PUBLIC_URL}/{r2_key}"


def get_r2_image_bytes(r2_key: str) -> bytes:
    """Download an object from R2 and return its raw bytes."""
    try:
        response = s3.get_object(Bucket=R2_BUCKET, Key=r2_key)
        return response["Body"].read()
    except Exception as e:
        print(f"[r2_client] get_r2_image_bytes error for key '{r2_key}': {e}")
        raise


def delete_image(r2_key: str):
    """Delete an object from R2."""
    try:
        s3.delete_object(Bucket=R2_BUCKET, Key=r2_key)
    except Exception as e:
        print(f"[r2_client] delete_image error for key '{r2_key}': {e}")
        raise


# ---------------------------------------------------------------------------
# Batch product-image ingestion
# ---------------------------------------------------------------------------

def upload_product_images(
    product_id: str,
    domain: str,
    image_urls: list[str],
    max_images: int = 10,
) -> list[str]:
    """Download up to *max_images* from *image_urls*, convert each to WebP,
    upload to R2 under ``products/{domain}/{product_id}/{i:03d}.webp``, and
    return the list of R2 keys that were successfully stored.

    Failed downloads / conversions are skipped with an error log.
    """
    r2_keys: list[str] = []
    urls_to_process = image_urls[:max_images]

    for i, url in enumerate(urls_to_process):
        try:
            # Download the source image
            response = httpx.get(url, timeout=15, follow_redirects=True)
            response.raise_for_status()
            raw_bytes = response.content

            # Convert to WebP
            webp_bytes = convert_to_webp(raw_bytes)

            # Determine R2 key
            r2_key = f"products/{domain}/{product_id}/{i:03d}.webp"

            # Upload
            upload_image(webp_bytes, r2_key, content_type="image/webp")
            r2_keys.append(r2_key)

            # Polite delay between uploads
            if i < len(urls_to_process) - 1:
                time.sleep(0.3)

        except httpx.HTTPStatusError as e:
            print(
                f"[r2_client] upload_product_images: HTTP {e.response.status_code} "
                f"downloading '{url}' -- skipping"
            )
        except httpx.RequestError as e:
            print(
                f"[r2_client] upload_product_images: request error "
                f"downloading '{url}': {e} -- skipping"
            )
        except Exception as e:
            print(
                f"[r2_client] upload_product_images: unexpected error "
                f"for '{url}': {e} -- skipping"
            )

    return r2_keys
