from Crypto.Cipher import AES
from aiohttp import web, web_request
from tools import *
from config import *
import aiofiles
from os import path
import os
from captcha_check import captcha_check
from ext.FileManager import FileManager as fm
import sys

__VERSION__ = "1.1"

app = web.Application(client_max_size=max_bytes)
routes = web.RouteTableDef()
FileManager = fm()
total_size = 0

HTTPBadRequest = web.HTTPBadRequest(text="Bad Request")
HTTPSorryTotalSizeLimited = web.HTTPNotAcceptable(text="죄송합니다. 서버에서 설정한 최대 용량을 초과했습니다. 며칠 후 다시 시도해주세요.")

with open("./html/form.html", "r", encoding="utf-8") as f:
    main_html = f.read()
with open("./html/image_dec_form.html", "r", encoding="utf-8") as f:
    dec_html = f.read()
with open("./html/upload.html", "r", encoding="utf-8") as f:
    uploaded_html = f.read()

def add_size(size: int):
    global total_size
    total_size += size

def size_boom():
    return total_size > max_size_limit

[ add_size(path.getsize(f"./files/{filename}")) for filename in os.listdir("./files") ]

print(f"Total size: {round(total_size/1024/1024)}MB")

@routes.get("/")
async def main_page(request):
    return web.Response(text=main_html, content_type="text/html")

@routes.get("/{file_name}")
async def get_file(request: web.Request):
    file_name = request.match_info.get("file_name", "None")

    if file_name == "None":
        return HTTPBadRequest
    
    if file_name == shutdown_key:
        print("Server Shutdown command received. Shutting down...")
        await FileManager.delete_expired()
        await app.shutdown()
        await app.cleanup()
        print("End.")
        sys.exit(0)
    
    if path.exists(f"./files/{file_name}"):
        return web.Response(
            text=dec_html
                .replace("{{--File--}}", file_name)
                .replace("{{--Searches--}}", str(FileManager.get_seaches(file_name))), 
            content_type="text/html")
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
        data["h-captcha-response"]
    except:
        return HTTPBadRequest
    
    password = data["password"]

    if not isinstance(password, str) or len(password) > 16 or not is_eng_digits(password):
        return HTTPBadRequest
    
    if not await captcha_check(data["h-captcha-response"]):
        return HTTPBadRequest
    
    password = password_formatter(password)

    async with aiofiles.open(f"./files/{file_name}", "rb") as f:
        nonce, tag, ciphertext = [ await f.read(x) for x in (16, 16, -1) ]
    
    cipher = AES.new(password.encode("utf-8"), AES.MODE_EAX, nonce)

    try:
        decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
    except:
        return web.HTTPNotAcceptable(text="Password mismatch.")
    
    FileManager.add_searches(file_name)
    
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
    if size_boom():
        return HTTPSorryTotalSizeLimited

    IP = getIp(request)
    
    data = await request.post()

    try:
        data["file"]
        data["password"]
        data["h-captcha-response"]
    except:
        return HTTPBadRequest
    
    file = data["file"]
    password = data["password"]
    captcha_response = data["h-captcha-response"]

    
    if not isinstance(file, web_request.FileField) or not isinstance(password, str) or not isinstance(captcha_response, str):
        return HTTPBadRequest

    if password == "" or len(password) > 16:
        return HTTPBadRequest
    
    if not is_eng_digits(password):
        return HTTPBadRequest
    
    password = password_formatter(password)



    file_bytes = file.file.read()
    file_name = file.filename


    # Client max size = max_bytes. it probably won't be called. 
    if len(file_bytes) > max_bytes:
        return HTTPBadRequest
    
    if not await captcha_check(captcha_response):
        return HTTPBadRequest
    
    generated_filename = random_string() +"."+ file_name.split(".")[-1]

    while path.exists(f"./files/{generated_filename}"):
        generated_filename = random_string() +"."+ file_name.split(".")[-1]


    # Encryption
    cipher = AES.new(password.encode("utf-8"), AES.MODE_EAX)
    ciphertext, tag = cipher.encrypt_and_digest(file_bytes)
    
    async with aiofiles.open(f"files/{generated_filename}", "wb") as f:
        [ await f.write(x) for x in (cipher.nonce, tag, ciphertext) ]
    
    add_size(path.getsize(f"./files/{generated_filename}"))
    
    await FileManager.addfile(generated_filename, IP)
    return web.Response(text=uploaded_html.replace("{{--File--}}", generated_filename), content_type="text/html")
    


app.add_routes(routes)
print(f"Server Version: {__VERSION__}")
web.run_app(app, host="0.0.0.0", port=1234)