from pymongo import MongoClient, errors
import logging
import bcrypt
from datetime import datetime

from pymongo.errors import PyMongoError

logging.basicConfig(level=logging.INFO, format='\n%(asctime)s - %(levelname)s - %(message)s')
client = MongoClient("localhost", 27017)

db = client['store_p2']
cur_user = None


def initialize_db():
    try:
        db.create_collection('account')
        db.account.create_index([('username', 1)], unique=True)
        db.product.create_index([('name', 1)], unique=True)
        hashed_password = bcrypt.hashpw("admin".encode('utf-8'), bcrypt.gensalt())
        db["account"].insert_one(
            {"role": "admin", "username": "admin", "password": hashed_password, "timestamp": datetime.now()})
        db.create_collection('order')
        db.create_collection('product')

        logging.info("Collections successfully created.")
    except PyMongoError as e:
        logging.error(f"Error: {e}")


def cleanup_collections():
    try:
        db.drop_collection('order')
        db.drop_collection('account')
        db.drop_collection('product')
        logging.info("Collections successfully dropped.")
    except PyMongoError as e:
        logging.error(f" Error: {e}")


def valid_input(input_str, options: set):
    user_input = input(input_str)
    while user_input not in options:
        print("Invalid input")
        user_input = input(input_str)

    return user_input


def select_multiple(doc_arr, operation: str, collection_name: str):
    valid_options = set(map(str, range(1, len(doc_arr) + 1)))
    while True:
        user_input = input(f"Select {collection_name}s to {operation} separated by commas (v1, v2, v3): ")
        cleaned_input = set(item.strip() for item in user_input.split(","))
        correct_input = True
        selected_docs = []

        for idx, e in enumerate(cleaned_input):
            if e not in valid_options:
                correct_input = False
                selected_docs = []
                print("Invalid input.")
                break
            else:
                selected_docs.append(doc_arr[int(e) - 1])
        if correct_input:
            if operation == "delete":
                ids = [doc["_id"] for doc in selected_docs]
                result = db[collection_name].delete_many({"_id": {"$in": ids}})
                print(f"{result.deleted_count} documents deleted.")
                logging.info(f"Deleted {collection_name} ids = {ids}")
            elif operation == "update":
                fields = [key for key in db[collection_name].find_one().keys()]
                offset = 0
                if "timestamp" in fields:
                    offset += 1
                valid_options2 = set(map(str, range(1, len(fields) - offset)))
                valid_options2.add("")
                while True:
                    for i, field in enumerate(fields):
                        if field == "_id" or field == "timestamp":
                            continue
                        print(f"({i}) {field} ", end=" ")
                    print()
                    user_input = input(f"Select fields to skip separated by commas (v1, v2, v3): ")
                    cleaned_input = set(item.strip() for item in user_input.split(","))
                    correct_input2 = True
                    selected_fields = set()

                    for idx, e in enumerate(cleaned_input):
                        if e not in valid_options2:
                            correct_input2 = False
                            selected_fields = set()
                            print("Invalid input.")
                            break
                        else:
                            if e != "":
                                selected_fields.add(fields[int(e)])
                    if correct_input2:
                        break
                for doc in selected_docs:
                    updated_doc = {}
                    for field, value in doc.items():
                        if field == "_id" or field in selected_fields:
                            updated_doc[field] = value
                        elif field == "username" or field == "name":
                            while True:
                                new_name = input(f"Current {field}: {value}; New {field}: ")
                                if not check_existing(collection_name, field, new_name):
                                    updated_doc[field] = new_name
                                    break
                        elif field == "password":
                            while True:
                                new_password = input("Enter Password: ")
                                password_again = input("Re-enter Password: ")
                                if new_password != password_again:
                                    print("passwords did not match")
                                else:
                                    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                                    updated_doc[field] = hashed_password
                                    break
                        elif field == "timestamp":
                            updated_doc[field] = value

                        elif field == "role":
                            print(f"Current role: {value}; Select role.")
                            selected_role = valid_input("(1) Admin (2) User", {"1", "2"})
                            if selected_role == "1":
                                updated_doc[field] = "admin"
                            else:
                                updated_doc[field] = "user"

                        elif field == "price":  # any float
                            while True:
                                print(f"Current {field}: {value}; New {field}: ")
                                new_val = input()
                                try:
                                    new_val = float(new_val)
                                    updated_doc[field] = new_val
                                    break
                                except ValueError:
                                    print(f"Error input is not numeric.")

                        else:
                            print(f"Current {field}: {value}; New {field}: ")
                            new_val = input()
                            updated_doc[field] = new_val

                    db[collection_name].replace_one({"_id": doc["_id"]}, updated_doc)
                    if len(fields) != len(selected_fields) + 1:
                        logging.info(f"Updated {collection_name} with id: {updated_doc['_id']}")
            elif operation == "order":
                new_order = {"account": cur_user, "items": selected_docs, "timestamp": datetime.now()}
                db["order"].insert_one(new_order)
                logging.info(f"Order placed: {new_order['_id']}")
            else:
                raise Exception("something broke")
        break


def register_account():
    while True:
        username = input("Enter Username: ")
        if not check_existing("account", "username", username):
            break

    while True:
        password = input("Enter Password: ")
        password_again = input("Re-enter Password: ")
        if password != password_again:
            print("passwords did not match")
        else:
            break

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db["account"].insert_one(
        {"username": username, "password": hashed_password, "role": "user", "timestamp": datetime.now()})


def login():
    global cur_user

    username = input("Enter Username: ")
    password = input("Enter Password: ")
    user = db["account"].find_one({"username": username})
    if user:
        if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            cur_user = user
            logging.info(f"{cur_user['username']} successfully logged in.")
            return True
        else:
            print("Password or username is incorrect.")
    else:
        print("Password or username is incorrect.")
    return False


def check_existing(collection_name: str, field: str, value):
    existing_value = db[collection_name].find_one({field: value})
    if existing_value:
        print(f"Invalid {field}. {field} already exists!")
        return True
    return False


def edit_products():
    while True:
        usr_input = valid_input("(1) View All (2) Add (3) Update (4) Delete (5) Exit ", {"1", "2", "3", "4", "5"})
        if usr_input == "1":
            view_products()
        elif usr_input == "2":
            while True:
                name = input("Product Name: ")
                if not check_existing("product", "name", name):
                    break
            while True:
                price = input("Product Price: ")
                try:
                    price = float(price)
                    break
                except ValueError:
                    print("Error price is not numeric.")
            new_product = {"name": name, "price": price}
            db["product"].insert_one(new_product)
            logging.info(f"{cur_user['username']} added {new_product}")

        elif usr_input == "3":
            update_products()
        elif usr_input == "4":
            delete_products()
        elif usr_input == "5":
            break
        else:
            raise Exception("Something broke")


def update_accounts():
    accounts = list(db["account"].find())
    if not accounts:
        print("No accounts to update.")
    else:
        view_all_accounts()
        select_multiple(accounts, "update", "account")


def delete_accounts():
    accounts = list(db["account"].find())
    if not accounts:
        print("No accounts to delete.")
    else:
        view_all_accounts()
        select_multiple(accounts, "delete", "account")


def edit_accounts():
    while True:
        usr_input = valid_input("(1) View All (2) Add (3) Update (4) Delete (5) Exit ", {"1", "2", "3", "4", "5"})
        if usr_input == "1":
            view_all_accounts()
        elif usr_input == "2":
            register_account()
        elif usr_input == "3":
            update_accounts()
        elif usr_input == "4":
            delete_accounts()
        elif usr_input == "5":
            break
        else:
            raise Exception("Something broke")


def view_products():
    products = db["product"].find()
    for i, product in enumerate(products):
        print(f"({i + 1}) {product['name']}: ${product['price']:.2f}")


def delete_products():
    products = list(db["product"].find())
    if not products:
        print("No products to delete.")
    else:
        view_products()
        select_multiple(products, "delete", "product")


def update_products():
    products = list(db["product"].find())
    if not products:
        print("No products to update.")
    else:
        view_products()
        select_multiple(products, "update", "product")


def make_order():
    products = list(db["product"].find())
    if not products:
        print("No products to order.")
    else:
        view_products()
        select_multiple(products, "order", "order")


def view_my_orders():
    for i, order in enumerate(db["order"].find({"account": cur_user})):
        print(f"({i + 1}) Order: {order['_id']} | Account: {order['account']['username']} ")
        print("-" * 20)
        print("Products")
        for j, item in enumerate(order["items"]):
            print(f"     ({j + 1}) {item['name']}: ${item['price']:.2f}")
        print("-" * 20)
        print(f"Timestamp: {order['timestamp']}")
        print()


def view_all_orders():
    for i, order in enumerate(db["order"].find()):
        print(f"({i + 1}) Order: {order['_id']} | Account: {order['account']['username']} ")
        print("-" * 20)
        print("Products")
        for j, item in enumerate(order["items"]):
            print(f"     ({j + 1}) {item['name']}: ${item['price']:.2f}")
        print("-" * 20)
        print(f"Timestamp: {order['timestamp']}")
        print()


def view_all_accounts():
    print("-" * 20)
    print("Users:")
    accounts = db["account"].find()
    for i, account in enumerate(accounts):
        print(
            f"({i + 1}) Username: {account['username']} - Role: {account['role']} - Created at: {account['timestamp']}")
    print("-" * 20)


initialize_db()
while True:
    input1 = valid_input("(1) Register (2) Login (3) Exit", {"1", "2", "3"})
    if input1 == "1":
        register_account()
        continue
    elif input1 == "2":
        if login():
            print(f"Welcome {cur_user['username']}")
        else:
            continue
    elif input1 == "3":
        break
    else:
        raise Exception("Something broke")

    while True:
        print("-" * 100)
        if cur_user["role"] == "user":
            input2 = valid_input("(1) View Products (2) Make Order (3) View My Orders (4) Logout", {"1", "2", "3", "4"})
            if input2 == "1":
                view_products()
            elif input2 == "2":
                make_order()
            elif input2 == "3":
                view_my_orders()
            elif input2 == "4":
                break
            else:
                raise Exception("Something broke")

        elif cur_user["role"] == "admin":
            input2 = valid_input(
                "(1) View Products (2) Edit Products (3) Make Order (4) View Orders (5) View All Orders "
                "(6) View All Accounts (7) Edit Accounts (8) Logout",
                {"1", "2", "3", "4", "5", "6", "7", "8"})

            if input2 == "1":
                view_products()
            elif input2 == "2":
                edit_products()
            elif input2 == "3":
                make_order()
            elif input2 == "4":
                view_my_orders()
            elif input2 == "5":
                view_all_orders()
            elif input2 == "6":
                view_all_accounts()
            elif input2 == "7":
                edit_accounts()
            elif input2 == "8":
                logging.info(f"{cur_user['username']} logged out.")
                break
            else:
                raise Exception("Something broke")
        else:
            raise Exception("Unknown role")

save = valid_input("Would you like to drop collections? (1) Yes (2) No", {"1", "2"})
if save == "1":
    cleanup_collections()
