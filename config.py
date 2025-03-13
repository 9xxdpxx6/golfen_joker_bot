import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция для чтения токена из файла
def read_token_from_file(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('BOT_TOKEN='):
                return line.split('=')[1].strip()
    return None