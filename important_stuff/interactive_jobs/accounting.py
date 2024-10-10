import discord
from discord import ui
from random import randint
import psycopg2
from discord.utils import MISSING

connector = psycopg2.connect(
    dbname="=",
    user="=",
    password="=",
    host="=",
    port=""
)

postcurse = connector.cursor() 
postcurse.connection.autocommit = True


symbols = ['+', '-']

class AccountingMath(ui.Modal, title="Crunch Those Numbers"):
    def __init__(self):
        super().__init__(title="Crunch Those Numbers")
        self.random_questions = []
        for i in range(3):
            random_numer1 = randint(1, 100)
            random_numer2 = randint(1, 100)
            random_symbol = symbols[randint(0, len(symbols)-1)]

            question = ui.TextInput(label=f"{random_numer1} {random_symbol} {random_numer2} = ?", placeholder="Answer here", style=discord.TextStyle.short)
            self.add_item(question)
            answer = random_numer1 + random_numer2 if random_symbol == '+' else random_numer1 - random_numer2 if random_symbol == '-' else random_numer1 * random_numer2
            self.random_questions.append((question, answer))

    async def on_submit(self, interaction: discord.Interaction):
        
        correct1_random_number = randint(700, 1600)
        correct2_random_number = randint(1600, 3200)
        correct3_random_number = randint(3200, 8200)
        correct = 0
        correct_random_response1 = [
            f"You were only able to get one correct, the boss has paid you ${correct1_random_number}",
            f"The boss is dissapointed, but due to your efforts, you were still given ${correct1_random_number}",
            f"Only one answer was correct, this has been noted down and you have been paid ${correct1_random_number}",
            f"The boss thinks that you lied on your resume, you were still paid ${correct1_random_number}",
            f"Hours of work yet only work that should be labled as 'good enough', heres ${correct1_random_number}. Maybe think about a different career path",
            f"As you finish up your work, your supervisor looks over your shoulder and points out the incorrect numbers. Sttill, you were paid ${correct1_random_number}",
        ]

        correct_random_response2 = [
            f"Two correct answers, you have been paid ${correct2_random_number}"
            f"You seem to be getting the hang of this, heres ${correct2_random_number} for your efforts",
            f"One more and you would have been employee of the month, take {correct2_random_number} for doing what you can",
            f"Your supervisor is fine with the results, he gives you {correct2_random_number} for your hard work",
            f"Not the worst but not the best, heres ${correct2_random_number}, get yourself something... decent",
            f"Good effort but not enough, take ${correct2_random_number} and try to do better tomorrow"
        ]

        correct_random_response3 = [
            f"Wow! You are a model employee, you were given {correct3_random_number}",
            f"Your supervisor is impressed, he gives you {correct3_random_number} for your hard work",
            f"You are at hard crunching those numbers!, heres {correct3_random_number} go get yourself something nice!",
            f"You've reached employee of the day status! Heres {correct3_random_number}, couple more and you might get employee of the month!",
            f"We did not make a mistake hiring you for sure, take {correct3_random_number} I would like to see you tomorrow",
            f"Outstanding work! You might be one of the best accountants here! Take {correct3_random_number} and keep up the good work!"
        ]

        none_correct_random = [
            "Very disappointing, please try harder tomorrow, take $300 for encouragement",
            "This is not good, take $300 and do better next time",
            "Did your employer not even look over your resume? Just take $300 and do /job quit because clearly this isn't for you",
            "You seem to not be good at numbers, while you are still paid $300, you should consider a different career path",
            "So are you just bad with numbers or are you joking? Take $300 and go",
            "Guess it was an off day today, heres $300 and get some rest"
        ]
        for question, answer in self.random_questions:
            if question.value == str(answer):
                correct += 1
        if correct == 1:
            random_response = correct_random_response1[randint(0, len(correct_random_response1)-1)]
            await interaction.response.send_message(random_response, ephemeral=True)
            postcurse.execute("UPDATE currency SET money = money + " + str(correct1_random_number) + " WHERE user_id = %s", (str(interaction.user.id),))
        elif correct == 2:
            random_response = correct_random_response2[randint(0, len(correct_random_response2)-1)]
            await interaction.response.send_message(random_response, ephemeral=True)
            postcurse.execute("UPDATE currency SET money = money + " + str(correct2_random_number) + " WHERE user_id = %s", (str(interaction.user.id),))
        elif correct == 3:
            random_response = correct_random_response3[randint(0, len(correct_random_response3)-1)]
            await interaction.response.send_message(random_response, ephemeral=True)
            postcurse.execute("UPDATE currency SET money = money + " + str(correct2_random_number) + " WHERE user_id = %s", (str(interaction.user.id),))
        else:
            random_response = none_correct_random[randint(0, len(none_correct_random)-1)]
            await interaction.response.send_message(random_response, ephemeral=True)
            postcurse.execute(f"UPDATE currency SET money = money + 300 WHERE user_id = {str(interaction.user.id)}")

