from Crypto.Cipher import AES
from aiohttp import web, web_request
from tools import *
from config import *
import aiofiles
from os import path
from io import BytesIO

app = web.Application()
routes = web.RouteTableDef()

HTTPBadRequest = web.HTTPBadRequest(text="Bad Request")
with open("./html/form.html", "r", encoding="utf-8") as f:
    main_html = f.read()
with open("./html/image_dec_form.html", "r", encoding="utf-8") as f:
    dec_html = f.read()

@routes.get("/")
async def main_page(request):
    return web.Response(text=main_html, content_type="text/html")

@routes.get("/{file_name}")
async def get_file(request: web.Request):
    file_name = request.match_info.get("file_name", "None")

    if file_name == "None":
        return HTTPBadRequest
    
    if path.exists(f"./files/{file_name}"):
        return web.Response(text=dec_html.replace("{{--File--}}", file_name), content_type="text/html")
    else:
        return web.HTTPNotFound(text="404 Not Found.")

@routes.post("/{file_name}")
async def post_file(request: web.Request):
    file_name = request.match_info.get("file_name", "None")

    if file_name == "None":
        return HTTPBadRequest
    
    # ERROR WTF
    if file_name == "post":
        return await file_upload(request)
    
    if not path.exists(f"./files/{file_name}"):
        return web.HTTPNotFound(text="404 Not Found.")
    
    data = await request.post()

    try:
        data["password"]
    except:
        return HTTPBadRequest
    
    password = data["password"]

    if not isinstance(password, str) or len(password) > 16 or not is_eng_digits(password):
        return HTTPBadRequest
    
    password = password_formatter(password)

    async with aiofiles.open(f"./files/{file_name}", "rb") as f:
        nonce, tag, ciphertext = [ await f.read(x) for x in (16, 16, -1) ]
    
    cipher = AES.new(password.encode("utf-8"), AES.MODE_EAX, nonce)

    try:
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
    except:
        return web.HTTPNotAcceptable(text="Password mismatch.")
    
    file_type = "application/octet-stream"
    file_ext = file_name.split(".")[-1]

    if file_ext == "png":
        file_type = "image/png"
    elif file_ext == "jpg" or file_ext == "jpeg":
        file_type = "image/jpeg"
    elif file_ext == "gif":
        file_type = "image/gif"
    elif file_ext == "mp4":
        file_type = "video/mp4"
    elif file_ext == "mp3":
        file_type = "audio/mp3"
    elif file_ext == "webp":
        file_type = "image/webp"
    elif file_ext == "webm":
        file_type = "video/webm"

    return web.Response(body=decrypted_data, content_type=file_type)

    


@routes.post("/post")
async def file_upload(request: web.Request):
    IP = getIp(request)
    
    data = await request.post()

    try:
        data["file"]
        data["password"]
    except:
        return HTTPBadRequest
    
    file = data["file"]
    password = data["password"]

    
    if not isinstance(file, web_request.FileField) or not isinstance(password, str):
        return HTTPBadRequest

    if password == "" or len(password) > 16:
        return HTTPBadRequest
    
    if not is_eng_digits(password):
        return HTTPBadRequest
    
    password = password_formatter(password)

    file_bytes = file.file.read()
    file_name = file.filename

    if len(file_bytes) > max_bytes: # 16MB
        return HTTPBadRequest
    
    generated_filename = random_string() +"."+ file_name.split(".")[-1]

    while path.exists(f"./files/{generated_filename}"):
        generated_filename = random_string() +"."+ file_name.split(".")[-1]


    # Encryption
    cipher = AES.new(password.encode("utf-8"), AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(file_bytes)
    
    async with aiofiles.open(f"files/{generated_filename}", "wb") as f:
        [ await f.write(x) for x in (cipher.nonce, tag, ciphertext) ]
    
    return web.Response(text=f"Saved. /{generated_filename}")
    


app.add_routes(routes)
web.run_app(app, host="0.0.0.0", port=1234)