import logging
import os
import time
import urllib.error
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s',
    level=logging.DEBUG,
    filename='program.log',
)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения {message}: {error}')
    else:
        logging.debug(f'Отправлено сообщение в чат: {message}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = f'Эндпоинт {response.url} не доступен.'
            raise ConnectionError(message)
        return response.json()
    except Exception as error:
        raise urllib.error.HTTPError(error)


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not response:
        raise KeyError('Словарь не найден.')

    if not isinstance(response, dict):
        raise TypeError('Пришел список, а не словарь в ответе.')

    if 'homeworks' not in response:
        raise KeyError('Отсутствие ожидаемый ключ в словаре.')

    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Пришел словарь, а не список в ответе.')

    if response.get('homeworks') is None:
        raise KeyError('Ожидаемый словарь пустой.')

    return response['homeworks']


def parse_status(homework):
    """Извлекает информацию о статусе домашней работы."""
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))

    if homework_name is None:
        raise KeyError('Отсутствует имя домашней работы.')

    if verdict is None:
        raise KeyError('Отсутстует ключ homework_status.')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not check_tokens():
        logging.critical(
            'Отсутствует обязательная переменная окружения.'
            'Программа принудительно остановлена.'
        )
        exit()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
                logging.error(message)
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
