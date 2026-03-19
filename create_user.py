import bcrypt
from database import SessionLocal
import models

db = SessionLocal()

login = input('login: ')
username = input("username: ")
password = input("password: ")

hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

user = models.User(
    login=login,
    username=username,
    password=hashed
)

db.add(user)
db.commit()

print("user created")