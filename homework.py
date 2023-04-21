import logging
import os
import time
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
    environment_variable = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    for variable in environment_variable:
        if not variable:
            logging.critical(
                f'Отсутствует обязательная переменная окружения: {variable}.'
                'Программа принудительно остановлена.'
            )
            return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Отправлено сообщение в чат: {message}')
    except Exception as error:
        logging.error(f'Сбой при отправке сообщения {message}: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            message = f'Эндпоинт {response.url} не доступен.'
            logging.error(message)
            raise ConnectionError(message)
        return response.json()
    except Exception as error:
        logging.error(f'Статус ошибки {error}')
        raise str(error)


def check_response(response):
    """Проверяет ответ API на соответствие."""
    if not response:
        message = 'Словарь не найден.'
        logging.error(message)
        raise KeyError(message)

    if type(response) != dict:
        message = 'Пришел список, а не словарь.'
        logging.error(message)
        raise TypeError(message)

    if 'homeworks' not in response:
        message = 'Отсутствие ожидаемый ключ в словаре.'
        logging.error(message)
        raise KeyError(message)

    if type(response.get('homeworks')) != list:
        message = 'Пришел словарь, а не список в ответе.'
        logging.error(message)
        raise TypeError(message)

    return response['homeworks']


def parse_status(homework):
    """Извлекает информацию о статусе домашней работы."""
    if not homework.get('homework_name'):
        homework_name = 'Пусто'
        message = 'Отсутствует имя домашней работы.'
        logging.warning(message)
        raise KeyError(message)
    homework_name = homework.get('homework_name')

    homework_status = homework.get('status')
    if not homework_status:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)
        raise KeyError(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Cтатус домашней работы отсутсвует'
        logging.error(message)
        raise KeyError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    if not check_tokens():
        exit()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if type(response) != dict:
                raise TypeError(response)
            for homework in homeworks:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
