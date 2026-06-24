from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel
import sqlite3 as sql
from datetime import date
import pandas as pd
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

app = FastAPI()

SECRET_KEY =  'JamesBond'
algo = 'HS256'

oauth_scheme = OAuth2PasswordBearer(tokenUrl='login')
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)

# noinspection PyTypeChecker
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(
    GZipMiddleware,
minimum_size=1000
)

class Product(BaseModel):
    id : int
    name : str
    category : str
    price : float
    location: str
    created_date : date

def create_token(username:str):
    payload={
        'user': username,
        'exp': datetime.utcnow() + timedelta(minutes=60)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=algo
    )

def database():
    """Create the database connection, also contains piece of code to load the data"""
    con = sql.connect("products.db",check_same_thread=False)
    # data = pd.read_csv('products.csv')
    # data.to_sql('products', con,index=False)
    try:
        yield con
    finally:
        con.close()

@app.post('/login')
@limiter.limit("5/minute")
def login(request:Request,data:OAuth2PasswordRequestForm = Depends(),db=Depends(database)):
    results = pd.read_sql("SELECT * from users WHERE username = ?",db, params=(data.username,))
    if results.empty:
        raise HTTPException(status_code=401, detail="User not found")
    if data.password != results.iloc[0]['password']:
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_token(data.username)
    return {'access_token':token,'token_type':'bearer'}

async def get_current_user(token: str = Depends(oauth_scheme)):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[algo]
        )
        username = payload.get('user')
        if username is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )
        return username
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

@app.get('/products')
@limiter.limit("100/minute")
async def get_products(request:Request, limit: int = 100,offset: int = 0,cuser:str = Depends(get_current_user),db=Depends(database)):
    """GET ALL PRODUCTS"""
    results = pd.read_sql('SELECT * FROM products LIMIT ? OFFSET ?', db, params=(limit,offset))
    return results.to_dict(orient='records')

@app.get('/products/{rid}')
async def get_product_by_id(rid: int, cuser:str = Depends(get_current_user),db=Depends(database)):
    """Get Product by ID"""
    results = pd.read_sql('SELECT * FROM products WHERE id = ?', db,params=(rid,))
    if results.size == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return results.to_dict(orient='records')

@app.post('/products/')
async def create_product(product: Product, cuser:str = Depends(get_current_user), db=Depends(database)):
    """Create a new product with parameters (id, name, category, price, location, created_date)"""
    cur = db.cursor()
    product = product.model_dump()
    results = pd.read_sql('SELECT * FROM products WHERE id = ?',db,params=(product['id'],))
    if results.size != 0:
        raise HTTPException(status_code=409, detail="Product already exists")
    else:
        cur.execute('INSERT INTO PRODUCTS VALUES(?,?,?,?,?,?)',(product["id"],product["name"],product["category"],product["price"],product["location"],product['created_date']))
        db.commit()
        return {'Message': 'Product created'}

@app.delete('/products/{rid}')
async def delete_product(rid: int, cuser:str = Depends(get_current_user), db=Depends(database)):
    """Delete Product by ID"""
    results = pd.read_sql('SELECT * FROM products WHERE id = ?', db, params=(rid,))
    if results.size == 0:
        raise HTTPException(status_code=409, detail="Product not found")
    else:
        cur = db.cursor()
        cur.execute('DELETE FROM products WHERE id = ?',(rid,))
        db.commit()
        return {'Message': 'Product deleted'}

@app.put('/products/{rid}')
async def update_product(rid: int, product: Product, cuser:str = Depends(get_current_user),db=Depends(database)):
    """Update Product by ID"""
    results = pd.read_sql('SELECT * FROM products WHERE id = ?', db, params=(rid,))
    if results.size == 0:
        raise HTTPException(status_code=409, detail="Product not found")
    else:
        cur = db.cursor()
        pid,name, category, price, location, created_date = product.model_dump().values()
        cur.execute('UPDATE products SET id = ?, name=?, category = ?,price =?, location =?, created_date = ? WHERE id = ?',(pid,name,category,price,location,created_date,rid))
        db.commit()
        return {'Message': 'Product updated'}

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Not found"}
    )