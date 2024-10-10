# import pymongo
# import discord
# from pymongo import MongoClient
# from discord import app_commands
# from discord import Interaction
# import tempfile

# class TransactionService:
#     def __init__(self):
#         self.client = MongoClient('')
#         self.db = self.client['test']
#         self.collection = self.db[str(discord.user.User.id)]
    
#     def payment_transaction(self, user_id, user_id2, amount):
#         transaction_data = {
#             'user_id': user_id,
#             'paid to': user_id2,
#             'amount': amount
#         }
#         self.collection.insert_one(transaction_data)
#         return transaction_data

#     def bought_transaction(self, user_id, item, quantity):
#         transaction_data = {
#             'user_id': user_id,
#             'bought': item,
#             'quantity': quantity
#         }
#         self.collection.insert_one(transaction_data)
#         return transaction_data
#     def get_transactions(self, user_id):
#         transactions = []
#         for transaction in self.collection.find({'user_id': user_id}):
#             transactions.append(transaction)
#         with tempfile.NamedTemporaryFile(suffix=".txt") as temp:
#             temp.write('\n'.join(str(transaction) for transaction in transactions).encode())
#             temp_file_path = temp.name
#             return temp_file_path
        
    

    
    

        