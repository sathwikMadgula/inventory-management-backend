from fastapi import FastAPI, BackgroundTasks
from tortoise.contrib.fastapi import register_tortoise
from models import (supplier_pydantic, supplier_pydanticIn, Supplier,
                    Product, product_pydantic, product_pydanticIn)
from dotenv import dotenv_values
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request
from typing import List
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
import os

# Load env_config
env_config = dotenv_values(".env")

EMAIL = env_config.get("EMAIL") or os.getenv("EMAIL")
PASS = env_config.get("PASS") or os.getenv("PASS")
CORS_ORIGINS = env_config.get("CORS_ORIGINS") or os.getenv("CORS_ORIGINS")


app = FastAPI()

# ✅ CORS setup
print("-----------------\nCORS ORIGIN:",env_config)
origins = CORS_ORIGINS.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def index():
    return {"Msg": "go to /docs for the API documentation"}

# Supplier CRUD
@app.post("/supplier")
async def add_supplier(supplier_info: supplier_pydanticIn):
    supplier_obj = await Supplier.create(**supplier_info.dict(exclude_unset=True))
    response = await supplier_pydantic.from_tortoise_orm(supplier_obj)
    return {"status": "ok", "data": response}

@app.get("/supplier")
async def get_all_suppliers():
    response = await supplier_pydantic.from_queryset(Supplier.all())
    return {"status": "ok", "data": response}

@app.get("/supplier/{supplier_id}")
async def get_specific_supplier(supplier_id: int):
    response = await supplier_pydantic.from_queryset_single(Supplier.get(id=supplier_id))
    return {"status": "ok", "data": response}

@app.put("/supplier/{supplier_id}")
async def update_supplier(supplier_id: int, update_info: supplier_pydanticIn):
    supplier = await Supplier.get(id=supplier_id)
    update_info = update_info.dict(exclude_unset=True)
    for field, value in update_info.items():
        setattr(supplier, field, value)
    await supplier.save()
    response = await supplier_pydantic.from_tortoise_orm(supplier)
    return {"status": "ok", "data": response}

@app.delete("/supplier/{supplier_id}")
async def delete_supplier(supplier_id: int):
    await Supplier.get(id=supplier_id).delete()
    return {"status": "ok"}

# Product CRUD
@app.post("/product/{supplier_id}")
async def add_product(supplier_id: int, product_details: product_pydanticIn):
    supplier = await Supplier.get(id=supplier_id)
    data = product_details.dict(exclude_unset=True)
    data["revenue"] = float(data.get("quantity_sold", 0)) * float(data.get("unit_price", 0))
    product_obj = await Product.create(**data, supplied_by=supplier)
    response = await product_pydantic.from_tortoise_orm(product_obj)
    return {"status": "ok", "data": response}

@app.get("/product")
async def all_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {"status": "ok", "data": response}

@app.get("/product/{id}")
async def specific_product(id: int):
    response = await product_pydantic.from_queryset_single(Product.get(id=id))
    return {"status": "ok", "data": response}

@app.put("/product/{id}")
async def update_product(id: int, update_info: product_pydanticIn):
    product = await Product.get(id=id)
    update_data = update_info.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    await product.save()
    response = await product_pydantic.from_tortoise_orm(product)
    return {"status": "ok", "data": response}

@app.delete("/product/{id}")
async def delete_product(id: int):
    await Product.filter(id=id).delete()
    return {"status": "ok"}

# Email setup
class EmailContent(BaseModel):
    message: str
    subject: str

conf = ConnectionConfig(
    MAIL_USERNAME=EMAIL,
    MAIL_PASSWORD=PASS,
    MAIL_FROM=EMAIL,
    MAIL_PORT=465,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

@app.post("/email/{product_id}")
async def send_email(product_id: int, content: EmailContent):
    try:
        product = await Product.get(id=product_id)
        supplier = await product.supplied_by
        supplier_email = [supplier.email]

        html = f"""
        <h5>Sathwik Athreya Business LTD</h5>
        <br>
        <p>{content.message}</p>
        <br>
        <p>Best Regards</p>
        <h6>Sathwik Business LTD</h6>
        """

        message = MessageSchema(
            subject=content.subject,
            recipients=supplier_email,
            body=html,
            subtype=MessageType.html
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        return {"status": "ok", "message": "Email sent successfully"}

    except Exception as e:
        print("EMAIL ERROR:", e)
        return JSONResponse(status_code=500, content={"status": "error", "detail": str(e)})

# Database
register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)

