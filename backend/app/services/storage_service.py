"""Servicio para gestión de almacenamiento de objetos (S3 / Cloudflare R2 / Neon Storage)."""

import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import BinaryIO, Optional
from app.core.config import settings

def get_s3_client():
    """Crea y devuelve un cliente de S3 configurado con las credenciales de entorno."""
    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return None

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_ENDPOINT_URL_S3,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )

def upload_file_to_s3(
    file_obj: BinaryIO,
    filename: str,
    content_type: str,
    folder: str = "vehicle_images",
) -> str:
    """
    Sube un archivo a S3 y devuelve su URL pública/accesible.
    Si S3 no está configurado, lanza RuntimeError o devuelve None.
    """
    client = get_s3_client()
    if not client:
        raise RuntimeError("Credenciales de S3 no configuradas en el entorno.")

    bucket = settings.S3_BUCKET_NAME
    key = f"{folder}/{filename}" if folder else filename

    extra_args = {"ContentType": content_type}
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)

    # Generar URL pública
    if settings.AWS_ENDPOINT_URL_S3:
        endpoint = settings.AWS_ENDPOINT_URL_S3.rstrip("/")
        return f"{endpoint}/{bucket}/{key}"
    
    return f"https://{bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
