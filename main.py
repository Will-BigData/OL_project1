from pymongo import MongoClient
import logging
import bcrypt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
client = MongoClient("localhost", 27017)

db = client['store_p2']
cur_user = ""

try:
    db.create_collection('account')
    db.create_collection('order')
    db.create_collection('product')
    logging.info("Collections successfully created")
except Exception as e:
    logging.error(f"Failed to create collections. Error: {e}", )


def valid_input(input_str, options: set):
    user_input = input(input_str)
    while user_input not in options:
        print("Invalid input")
        user_input = input(input_str)

    return user_input


def register_account():
    existing_user = None
    col = db["account"]
    while True:
        username = input("Enter Username: ")
        existing_user = db['account'].find_one({"username": username})
        if existing_user:
            print("Invalid username. Username already exists!")
        else:
            break

    correct_password = False
    while True:
        password = input("Enter Password: ")
        password_again = input("Re-enter Password: ")
        if password != password_again:
            print("passwords did not match")
        else:
            break

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db["account"].insert_one({"username": username, "password": hashed_password, "admin": "user"})


def login():
    nonlocal cur_user

    username = input("Enter Username: ")
    password = input("Enter Password: ")
    user = db["account"].find_one({"username": username})
    if user:
        if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            x = user["password"]
            cur_user = user
            print("Successfully logged in!")
        else:
            print("Could not login")


def edit_products():
    valid_input("(1) Add (2) Update (3) Delete (4) Exit", {"1", "2", "3", "4"})

while True:
    input1 = valid_input("(1) Register (2) Login (3) Exit", {"1", "2", "3"})
    if input1 == "1":
        register_account()
    elif input1 == "2":
        login()
        break
    elif input1 == "3":
        break
    else:
        raise Exception("Something broke")


# todo add user view
# add logging

# while True:
    print(f"Welcome {cur_user}")
    input2 = valid_input("(1) View Products (2) Edit Products (3) Make Order (4) View Orders", {"1", "2", "3", "4"})

    if input1 == "1":
        products = db["product"].find()
        for product in products:
            # todo format this
            print(product)
    elif input1 == "2":
        edit_products()

    elif input1 == "3":
        pass
    elif input1 == "4":
        pass
    else:
        raise Exception("Something broke")
