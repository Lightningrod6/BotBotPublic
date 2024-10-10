from psycopg2 import sql, connect
#from Bank.transaction_service import TransactionService
import json
from pymongo import MongoClient
import discord

connector = connect(
    dbname="",
    user="",
    password="",
    host="",
    port=""
)

class ItemsService:
    def __init__(self):
        #self.transaction_service = TransactionService()
        self.connection = connector
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()
        self.client = MongoClient('')
        self.db = self.client['test']
        self.collection = self.db[str(discord.user.User.id)]
        
    def sell_item(self, user_id, item_name, quantity_to_sell):
        collection = self.db[str(user_id)]
        item = collection.find_one({'item_name': item_name})
        if item is None:
            raise ValueError("Item was not found")
        item_quantity = item['count']
        item_value = item['item_details']['value']
        item_rarity = item['category']
        total_value = quantity_to_sell * item_value

        # Check if the user has enough of the item to sell
        if item_quantity < quantity_to_sell:
            raise ValueError("Not enough items to sell")

        # Subtract from the count
        collection.update_one({'item_name': item_name}, {'$inc': {'count': -quantity_to_sell}})

        # Delete the document if 'count' is zero
        item = collection.find_one({'item_name': item_name})
        if item and item['count'] == 0:
            collection.delete_one({'item_name': item_name})

        # Check if the item exists in the shop
        check_item = sql.SQL("SELECT item_quantity FROM shop_items WHERE item_name = %s")
        self.cursor.execute(check_item, (item_name,))
        result = self.cursor.fetchone()
        if result:
            # Item exists, update quantity
            new_quantity = result[0] + quantity_to_sell
            update_item = sql.SQL("UPDATE shop_items SET item_quantity = %s WHERE item_name = %s")
            self.cursor.execute(update_item, (new_quantity, item_name))
        else:
            # Item does not exist, add new item
            add_item = sql.SQL("INSERT INTO shop_items (item_name, item_rarity, item_cost, item_quantity) VALUES (%s, %s, %s, %s)")
            self.cursor.execute(add_item, (item_name, item_rarity, item_value, quantity_to_sell))

        self.cursor.execute("SELECT money FROM currency WHERE user_id = %s", (str(user_id),))
        user_money = self.cursor.fetchone()
        
        if user_money:
            current_balance = user_money[0]
        else:
            raise ValueError("User not found")
        
        new_balance = current_balance + total_value
        self.cursor.execute("UPDATE currency SET money = %s WHERE user_id = %s", (new_balance, str(user_id)))
        # Record the transaction
        #self.transaction_service.payment_transaction(user_id, 0, total_value)
    def buy_item(self, user_id, item_name, quantity_to_buy):
        # Check if the item exists in the shop
        check_item = sql.SQL("SELECT item_rarity, item_cost, item_quantity FROM shop_items WHERE item_name = %s")
        self.cursor.execute(check_item, (item_name,))
        result = self.cursor.fetchone()
        if result:
            item_rarity, item_value, item_quantity = result
            total_value = quantity_to_buy * item_value

            # Check if the shop has enough of the item to sell
            if item_quantity < quantity_to_buy:
                raise ValueError("Not enough items to buy")

            # Subtract from the count in the shop
            new_quantity = item_quantity - quantity_to_buy
            update_item = sql.SQL("UPDATE shop_items SET item_quantity = %s WHERE item_name = %s")
            self.cursor.execute(update_item, (new_quantity, item_name))
        else:
            raise ValueError("Item not found in shop")

        # Add to the user's inventory
        collection = self.db[str(user_id)]
        item = collection.find_one({'item_name': item_name})
        if item:
            collection.update_one({'item_name': item_name}, {'$inc': {'count': quantity_to_buy}})
        else:
            collection.insert_one({
                'category': item_rarity, 
                'item_name': item_name, 
                'item_details': {
                    'value': item_value, 
                    'icon': "null"
                    },
                "count": quantity_to_buy,
                }
            )

# {
#   "category": "Common",
#   "item_name": "Bottle cap",
#   "item_details": {
#     "value": 1,
#     "icon": null
#   },
#   "count": 2
# }
        # Subtract from the user's balance
        self.cursor.execute("SELECT money FROM currency WHERE user_id = %s", (str(user_id),))
        user_money = self.cursor.fetchone()
        if user_money:
            current_balance = user_money[0]
        else:
            raise ValueError("User not found")

        new_balance = current_balance - total_value
        if new_balance < 0:
            raise ValueError("Not enough money to buy items")

        self.cursor.execute("UPDATE currency SET money = %s WHERE user_id = %s", (new_balance, str(user_id)))

        # Record the transaction
        #self.transaction_service.payment_transaction(user_id, 0, -total_value)
    def get_item_value(self, item_name):
        with open("Gamble/items.json", "r") as file:
            items = json.load(file)

        for category in items.values():
            for item, details in category.items():
                if item == item_name:
                    return details['value']  # Return the item value

        raise ValueError(f"No item with the name {item_name} found")
testing = ItemsService()

print(testing.get_item_value("Switzerland"))