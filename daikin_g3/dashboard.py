"""Render a bounded sensor dashboard as a G3-compatible JPEG."""
from dataclasses import dataclass
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .images import prepare_image

@dataclass(frozen=True)
class Tile:
    label: str
    value: str
    unit: str = ""

def render_dashboard(title, tiles, *, font_path=None, theme="dark"):
    if not isinstance(title,str) or not 1<=len(title)<=80:
        raise ValueError("invalid title")
    if not isinstance(tiles,(list,tuple)) or not 1<=len(tiles)<=8:
        raise ValueError("one to eight tiles required")
    if theme not in ("dark","light"):
        raise ValueError("invalid theme")
    for t in tiles:
        if not isinstance(t,Tile) or any(not isinstance(s,str) or len(s)>80 for s in (t.label,t.value,t.unit)):
            raise ValueError("invalid tile")
    if font_path is None and any(ord(c)>255 for s in [title]+[s for t in tiles for s in (t.label,t.value,t.unit)] for c in s):
        raise ValueError("Unicode dashboard requires a suitable font_path")
    bg,card,fg,muted=("#101820","#22313f","#ffffff","#b6c8d4") if theme=="dark" else ("#edf2f6","#ffffff","#152534","#4b6274")
    image=Image.new("RGB",(480,854),bg)
    draw=ImageDraw.Draw(image)
    def font(size):
        return ImageFont.truetype(font_path,size) if font_path else ImageFont.load_default(size=size)
    def line(text,x,y,max_width,size,color):
        while size>=12:
            f=font(size)
            if draw.textlength(text,font=f)<=max_width:
                draw.text((x,y),text,font=f,fill=color)
                return
            size-=2
        f=font(12)
        while text and draw.textlength(text+"...",font=f)>max_width:
            text=text[:-1]
        draw.text((x,y),text+"...",font=f,fill=color)
    line(title,22,22,436,36,fg)
    cols=1 if len(tiles)<=4 else 2
    rows=(len(tiles)+cols-1)//cols
    w=(440-(cols-1)*12)//cols
    h=(754-(rows-1)*12)//rows
    for i,t in enumerate(tiles):
        x=20+(i%cols)*(w+12)
        y=80+(i//cols)*(h+12)
        draw.rounded_rectangle((x,y,x+w,y+h),radius=16,fill=card)
        line(t.label,x+14,y+14,w-28,24,muted)
        line(t.value,x+14,y+h//3,w-28,52 if cols==1 else 40,fg)
        line(t.unit,x+14,y+h-38,w-28,22,muted)
    out=BytesIO()
    image.save(out,format="PNG")
    return prepare_image(out.getvalue())

async def show_dashboard(album,title,tiles,*,font_path=None,theme="dark",**settings):
    import asyncio
    image=await asyncio.to_thread(render_dashboard,title,tiles,font_path=font_path,theme=theme)
    return await album.show(image.data,**settings)
