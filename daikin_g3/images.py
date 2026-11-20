"""Prepare baseline JPEG images for the G3 screen."""
from dataclasses import dataclass
from io import BytesIO
import zlib
from PIL import Image, ImageOps

@dataclass(frozen=True)
class PreparedImage:
    data: bytes
    width: int
    height: int
    crc32: int

def prepare_image(source, *, width=480, height=854, fit="contain", max_bytes=131072):
    if type(width) is not int or type(height) is not int or not 1<=width<=480 or not 1<=height<=854:
        raise ValueError("invalid screen dimensions")
    if type(max_bytes) is not int or not 1<=max_bytes<=131072:
        raise ValueError("invalid byte budget")
    if fit not in ("contain","cover"):
        raise ValueError("invalid fit")
    with Image.open(BytesIO(source)) as original:
        if original.width*original.height>25000000:
            raise ValueError("source too large")
        image=ImageOps.exif_transpose(original).convert("RGBA")
        background=Image.new("RGBA",image.size,"black")
        background.alpha_composite(image)
        image=background.convert("RGB")
        if fit=="cover":
            image=ImageOps.fit(image,(width,height),method=Image.Resampling.LANCZOS)
        else:
            image=ImageOps.pad(image,(width,height),method=Image.Resampling.LANCZOS,color="black")
    for quality in (90,85,80,75,70,60,50,40,30,20,10):
        output=BytesIO()
        image.save(output,format="JPEG",quality=quality,subsampling=2,progressive=False,optimize=True)
        data=output.getvalue()
        if len(data)<=max_bytes:
            return PreparedImage(data,width,height,zlib.crc32(data)&0xffffffff)
    raise ValueError("JPEG cannot fit byte budget")
