from pymongo import MongoClient, errors
import logging
import bcrypt
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
client = MongoClient("localhost", 27017)

db = client['store_p2']
# todo enable cur_user
cur_user = None


def initialize_db():
    try:
        db.create_collection('account')
        # todo comeback
        db.create_collection('order')

        # todo drop the collection and make sure this works, set up pymongo exception 
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


def select_multiple(doc_arr, operation: str):
    valid_options = set(map(str, range(1, len(doc_arr) + 1)))
    while True:
        user_input = input(f"Select products to {operation} separated by commas (v1, v2, v3): ")
        cleaned_input = set(item.strip() for item in user_input.split(","))
        correct_input = True
        selected_products = []

        for idx, e in enumerate(cleaned_input):
            if e not in valid_options:
                correct_input = False
                selected_products = []
                print("Invalid input.")
                break
            else:
                selected_products.append(doc_arr[int(e) - 1])
        if correct_input:
            if operation == "delete":
                ids = [product["_id"] for product in selected_products]
                result = db["product"].delete_many({"_id": {"$in": ids}})
                print(f"{result.deleted_count} documents deleted.")
                logging.info(f"\nDeleted product_ids = {ids}")
            elif operation == "update":
                for product in selected_products:
                    updated_product = {}
                    for field, value in product.items():
                        if field == "_id":
                            updated_product[field] = value
                        elif field == "price":  # any float
                            while True:
                                print(f"Current {field}: {value}; New {field}: ")
                                new_val = input()
                                try:
                                    new_val = float(new_val)
                                    updated_product[field] = new_val
                                    break
                                except ValueError:
                                    print(f"Error input is not numeric.")

                        else:
                            print(f"Current {field}: {value}; New {field}: ")
                            new_val = input()
                            updated_product[field] = new_val

                    db["product"].replace_one({"_id": product["_id"]}, updated_product)
                    logging.info(f"\nUpdated product with id: {updated_product['_id']}")
            elif operation == "order":
                new_order = {"account": cur_user, "items": selected_products, "timestamp": datetime.now()}
                db["order"].insert_one(new_order)
                logging.info(f"\nOrder placed: {new_order}")
            else:
                raise Exception("something broke")
        break


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
    global cur_user

    username = input("Enter Username: ")
    password = input("Enter Password: ")
    user = db["account"].find_one({"username": username})
    if user:
        if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
            cur_user = user
            print("Successfully logged in!")
        else:
            print("Could not login")


def edit_products():
    while True:
        usr_input = valid_input("(1) Add (2) Update (3) Delete (4) Exit", {"1", "2", "3", "4"})
        if usr_input == "1":
            name = input("Product Name: ")
            while True:
                price = input("Product Price: ")
                try:
                    price = float(price)
                    break
                except ValueError:
                    print("Error price is not numeric.")
            new_product = {"name": name, "price": price}
            db["product"].insert_one(new_product)
            logging.info(f"\n {cur_user} added {new_product}")

        elif usr_input == "2":
            update_products()
        elif usr_input == "3":
            delete_products()
        elif usr_input == "4":
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
        select_multiple(products, "delete")


def update_products():
    products = list(db["product"].find())
    if not products:
        print("No products to update.")
    else:
        view_products()
        select_multiple(products, "update")


def make_order():
    products = list(db["product"].find())
    if not products:
        print("No products to order.")
    else:
        view_products()
        select_multiple(products, "order")


# while True:
#     input1 = valid_input("(1) Register (2) Login (3) Exit", {"1", "2", "3"})
#     if input1 == "1":
#         register_account()
#     elif input1 == "2":
#         login()
#         break
#     elif input1 == "3":
#         break
#     else:
#         raise Exception("Something broke")

# print(f"Welcome {cur_user['username']}")


def view_orders():
    for i, order in enumerate(db["order"].find()):
        print(f"({i + 1}) Order: {order['_id']} | Account: {order['account']} ")
        print("-" * 20)
        print("Products")
        for j, item in enumerate(order["items"]):
            print(f"     ({j + 1}) {item['name']} | ${item['price']:.2f}")
        print("-" * 20)
        print(f"Timestamp: {order['timestamp']}")
        print()


while True:
    input2 = valid_input("(1) View Products (2) Edit Products (3) Make Order (4) View Orders (5) Exit "
                         "Program", {"1", "2", "3", "4", "5"})

    if input2 == "1":
        view_products()
    elif input2 == "2":
        edit_products()
    elif input2 == "3":
        make_order()
    elif input2 == "4":
        view_orders()
    elif input2 == "5":
        break
    else:
        raise Exception("Something broke")
