"""Сервер Telegram бота, запускаемый непосредственно"""
import os

import telebot
from flask import Flask, request
from telebot import types

from app import message_serializer, exceptions, settings, spreadsheet

API_TOKEN = os.environ.get('API_TOKEN')
AUTHOR_ID = int(os.environ.get('AUTHOR_ID'))

bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)


@server.route('/', methods=['GET'])
def index():
    return '<h1>Bot welcomes you!</h1>'


@server.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return ''


def is_mine(handler):
    def wrapper(message):
        if int(message.chat.id) != AUTHOR_ID:
            bot.send_message(message.chat.id, 'Permission denied')
            return
        return handler(message)
    return wrapper


@bot.message_handler(commands=['start', 'help'])
@is_mine
def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и помощь по боту"""
    bot.send_message(message.chat.id, text=
                     "Бот для учёта финансов\n\n"
                     "Добавить расход: 250 такси\n"
                     "Добавить доход: /i 1000 зарплата\n"
                     "Сегодняшняя статистика: /today\n"
                     "За текущий месяц: /month\n"
                     "Последние внесённые расходы: /expenses\n"
                     "Категории трат и доходов: /categories"
                     )


@bot.message_handler(commands=['categories'])
@is_mine
def categories_list(message: types.Message):
    """Отправляет список категорий расходов"""
    answer = message_serializer.get_categories(global_categories=True)
    bot.send_message(message.chat.id, answer, parse_mode='Markdown')


@bot.message_handler(commands=['today'])
@is_mine
def today_statistics(message: types.Message):
    """Отправляет сегодняшнюю статистику трат"""
    answer = message_serializer.get_today_statistics()
    bot.send_message(message.chat.id, answer)


@bot.message_handler(commands=['month'])
@is_mine
def month_statistics(message: types.Message):
    """Отправляет статистику трат текущего месяца"""
    answer = message_serializer.get_month_statistics()
    bot.send_message(message.chat.id, answer)


@bot.message_handler(commands=['expenses'])
@is_mine
def list_expenses(message: types.Message):
    """Отправляет последние несколько записей о расходах"""
    answer = message_serializer.get_latest()
    bot.send_message(message.chat.id, answer)


@bot.message_handler(func=lambda message: message.text.startswith('/del'))
@is_mine
def del_expense(message: types.Message):
    """Удаляет одну запись о расходе по её идентификатору"""
    row_id = int(message.text[4:])
    answer = message_serializer.delete_expense(row_id)
    bot.reply_to(message, answer)


@bot.message_handler(func=lambda message: True)
@is_mine
def add_items(message: types.Message):
    """Добавляет новые записи, одна строка = одна запись"""
    try:
        responses = message_serializer.add_items(message.text)
    except exceptions.NotCorrectMessage as e:
        answer = str(e)
    else:
        answer = ""
        for response in responses:
            try:
                amount = int(response.amount)
            except ValueError:
                amount = int(response.amount[:-1])

            category = response.description if response.category_name == settings.OTHER else response.category_name
            if type(response) is spreadsheet.Expense:
                answer += f"Добавлены траты {amount} {settings.CURRENCY} на {category}.\n"
            else:
                answer += f"Добавлен доход {amount} {settings.CURRENCY} на {category}.\n"

        answer += f"\n{message_serializer.get_today_statistics()}"
    bot.send_message(message.chat.id, answer)


if __name__ == '__main__':
    server.run()
