import os
import openai
import sqlite3
from openai import OpenAI
from tabulate import tabulate
from prompt import prompt
from food import getCalories
from colorama import Fore, Back, Style

# Set environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Create an OpenAPI client using the key from our environment variable
client = OpenAI(
    api_key=OPENAI_API_KEY,
)


def get_user_info():
    reason = "Provide some information on your eating habits(Allergens): \n"
    print("Please enter your information in the following questions:\n")
    user_input1 = input("What is your name? ")
    user_input2 = input("How old are you? ")
    user_input3 = input("Enter your current weight? (in lbs or kg): ")
    user_input4 = input("Enter your goal weight? (in lbs or kg): ")
    user_input5 = input(reason)

    return {
        "name": user_input1,
        "age": user_input2,
        "weight": user_input3,
        "goal_weight": user_input4,
        "reason": user_input5
    }


# checks if recommendations is in db, if not adds it
def update_db():
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if "recommendations" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN recommendations TEXT")
        engine.commit()
        engine.close()


# User data for the database
def input_userdata_into_db(user_data_for_db):
    # connects to db
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()

    # creates db table
    create_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            weight INTEGER,
            goal_weight INTEGER,
            reason TEXT,
            recommendations TEXT
        );
    '''

    cursor.execute(create_table)

    # insert user data in db table
    insert_user_into_table = '''
    INSERT INTO users (name, age, weight, goal_weight,reason,recommendations)
    VALUES(:name,:age,:weight,:goal_weight,:reason,:recommendations)
    '''

    cursor.execute(insert_user_into_table, user_data_for_db)
    engine.commit()
    engine.close()


def save_recommendations(user_id, recommendations):
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()
    task = "UPDATE users SET recommendations=? WHERE id=?"
    cursor.execute(task, (recommendations, user_id))
    engine.commit()
    engine.close()


def update_user_info(user_id, field, new_info):
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()
    task = f"UPDATE users SET {field}=? WHERE id=?"

    cursor.execute(task, (new_info, user_id))
    engine.commit()
    engine.close()


def clear_db():
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()

    cursor.execute("DELETE FROM users")
    engine.commit()
    engine.close()


# print db
def print_database():
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()

    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    reason = "RECOMMENDATIONS"
    header = ["ID", "NAME", "AGE", "WEIGHT", "Goal WEIGHT", "REASON", reason]
    print("User Data:\n")
    print(tabulate(rows, headers=header, tablefmt="grid"))
    engine.close()


def print_user_in_db():
    engine = sqlite3.connect("userdata.db")
    cursor = engine.cursor()

    cursor.execute("SELECT * FROM users ORDER BY ID DESC LIMIT 1")
    row = cursor.fetchone()

    reason = "RECOMMENDATIONS"
    header = ["ID", "NAME", "AGE", "WEIGHT", "Goal WEIGHT", "REASON", reason]
    print("Here is a copy of your info saved in our database: ")
    print(tabulate([row], headers=header, tablefmt="grid"))
    engine.close()


def call_openai(user_message):
    # Specify the model to use and the messages to send
    completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": user_message}
            ]
    )
    return completion.choices[0].message.content


def get_username(name):
    engine = sqlite3.connect('userdata.db')
    cursor = engine.cursor()

    cursor.execute("SELECT * FROM users WHERE name=?", (name,))
    user = cursor.fetchone()

    engine.close()
    return user


# parses the meals and calculates calories
def parse_options(options):
    response = ""

    for option in options:
        divider = option.find('|')
        name = option[2:divider-1]
        ingredients = (option[divider + 2:]).split(', ')
        calories = getCalories(ingredients)[-1]
        response += (
                f"- {name} ({Fore.CYAN}{calories}{Style.RESET_ALL} cals) | "
                f"{', '.join([i.capitalize() for i in ingredients])}"
                "\n"
        )
    return f"{response}\n"


# parses the chatgpt response
def parse_response(message):
    lines = message.split('\n')
    currMeal = 0
    response = """\nRecommended Meals with estimated calories:\n"""

    temp = []
    for line in lines:
        temp.append(line.strip())
    temp.append('')
    lines = temp

    for _ in range(3):
        for line in lines:
            line = line.strip()
            if line in ['Breakfast:', 'Lunch:', 'Dinner:']:
                response += f"{Fore.GREEN}{line.strip()}{Style.RESET_ALL}\n"
                curr = lines[currMeal+1:]
                end = curr.index('')
                response += parse_options(curr[:end])
                lines = curr[end+1:]
                currMeal = 0
                break
            currMeal += 1

    return response


def display_menu():
    print('''\n
        +--+--+--+--+--+--+--+--+
        |       Menu            |
        +--+--+--+--+--+--+--+--+
        | 1. Edit Name          |
        | 2. Edit Age           |
        | 3. Edit Weight.       |
        | 4. Edit Goal Weight   |
        | 5. Edit Reason        |
        | 6. Save/Exit          |
        +--+--+--+--+--+--+--+--+

    ''')


def edit_userdata(user_id):
    new_name = None
    while True:
        display_menu()
        select = "Enter the option to edit from the menu from 1 - 6: "
        selection = input(select).strip()
        if selection == "1":
            new_name = input("Enter a new name: ").strip()
            update_user_info(user_id, 'name', new_name)
        elif selection == "2":
            new_age = input("Enter a new age: ").strip()
            update_user_info(user_id, 'age', new_age)
        elif selection == "3":
            new_weight = input("Enter your new weight: ").strip()
            update_user_info(user_id, 'weight', new_weight)
        elif selection == "4":
            new_goal_weight = input("Enter your new goal weight: ").strip()
            update_user_info(user_id, 'goal_weight', new_goal_weight)
        elif selection == "5":
            reason = "Enter your info on current eating habits(Allergens): "
            new_reason = input(reason).strip()
            update_user_info(user_id, "reason", new_reason)
        elif selection == "6":
            break
        else:
            print("You did not enter a valid option!")
    return new_name


def main():
    print("Welcome to A.I. Food Advisor!\n")
    update_db()
    start = "Have you used this application before? (yes/no): "
    user_starter = input(start).strip().lower()

    if user_starter == 'yes':
        enter = "Please enter the name that you have previously entered: "
        user_name = input(enter).strip()
        user = get_username(user_name)

        if user:
            print(f"Welcome Back {user[1]}!")
            print("Here is your current information that we have from you: \n")
            rec = "RECOMMENDATIONS"
            header = ["NAME", "AGE", "WEIGHT", "Goal WEIGHT", "REASON", rec]
            user_data = [
                ["NAME", user[1]],
                ["AGE", user[2]],
                ["WEIGHT", user[3]],
                ["GOAL WEIGHT", user[4]],
                ["REASON", user[5]],
                ["RECOMMENDATIONS", user[6]]

            ]
            print(tabulate(user_data, headers=header, tablefmt="grid"))
            enter = "Would you like to edit your information? (yes/no): "
            edit_db = input(enter).strip().lower()
            if edit_db == 'yes':
                new_user = edit_userdata(user[0])
                if new_user:
                    user_name = new_user
                user = get_username(user_name)
            prompt = "Want more food recommendations? (yes/no): \n"
            more_recom = input(prompt)
            if more_recom == "yes":
                user_message = (
                    f"My name is {user[1]}, I am {user[2]} years old. "
                    f"I currently weigh {user[3]},"
                    f"my goal weight is {user[4]}. "
                    f"I want to eat healthier because currently {user[5]}. "
                )
                recommendations = parse_response(call_openai(user_message))
                print(recommendations)

                save_recommendations(user[0], recommendations)
                print_user_in_db()
            else:
                print("Thank you for visiting!")
        else:
            print("Sorry! User is not in database")
    else:
        user_data_for_db = get_user_info()

        user_message = (
            f"My name is {user_data_for_db['name']}, "
            f"I am {user_data_for_db['age']} years old. "
            f"I currently weigh {user_data_for_db['weight']}"
            f"and my goal weight is "
            f"{user_data_for_db['goal_weight']}. "
            f"I want to eat healthier because currently"
            f"{user_data_for_db['reason']}. "
        )
        recommendations = parse_response(call_openai(user_message))
        print(recommendations)
        user_data_for_db['recommendations'] = recommendations
        input_userdata_into_db(user_data_for_db)
        print_user_in_db()

        print("Thank you for visiting!")


if __name__ == "__main__":
    main()
