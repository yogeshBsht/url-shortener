import qrcode
import io
import base64
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()


def generate_qr_code(data: str, size: int = 10, border: int = 2) -> str:
    """
    Generate QR code as base64-encoded PNG.
    
    Args:
        data: Data to encode (URL)
        size: QR code box size
        border: Border size (minimum 4)
    
    Returns:
        Base64-encoded PNG image
    """
    if not settings.enable_qr_code:
        return None
    
    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=max(border, 4),  # Minimum border of 4
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    except Exception as e:
        logger.error("qr_code_generation_failed", error=str(e))
        return None