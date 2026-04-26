MAIN_TEXT = (
    "Привет! Благодарим тебя за покупку!\n\n"
    "Надеемся, что тебе понравился наш товар.\n"
    "В качестве благодарности за доверие, мы\n"
    "хотим сделать тебе подарок.\n\n"
    "— Чтобы его получить жми на кнопку\n"
    "«Получить подарок»\n\n"
    "— Чтобы обратиться в поддержку, жми на\n"
    "кнопку «Написать продавцу»"
)

SUPPORT_TEXT = "Выбери, пожалуйста, категорию обращения."

REVIEW_PRESENT_TEXT = (
    "У нас для тебя подарок за отзыв!\n\n"
    "Пожалуйста, введи свой номер телефона, "
    "на него мы отправим бонус!\n\n"
    "Или нажми на кнопку «Поделиться номером»"
)

# Commands
CMD_START = "start"
CMD_HELP = "help"
CMD_REVIEW = "review"
CMD_DESC_START = "Главное меню"
CMD_DESC_HELP = "Написать продавцу"
CMD_DESC_REVIEW = "Подарок за отзыв"

# Main menu / dialog buttons
BTN_GET_PRESENT = "Получить подарок"
BTN_CONTACT_SELLER = "Написать продавцу"
BTN_BACK = "⬅️ Назад"

# Support categories
CATEGORY_QUALITY = "Качество товара"
CATEGORY_BUNDLE = "Комплектация товара"
CATEGORY_OTHER = "Другой вопрос"
PHONE_NOT_SPECIFIED = "не указан"

# Keyboards / callbacks labels
BTN_SHARE_CONTACT = "Поделиться номером"
BTN_PHONE_OK = "Все верно 👍"
BTN_PHONE_RETRY = "Перепишу ✍️"
BTN_MANAGER_REQUEST_REVIEW = "Решено, запросить отзыв"
BTN_MANAGER_APPROVE = "Бонус отправлен 👍"
BTN_MANAGER_REJECT = "Отклонить ❌"

# Generic callback answers
CB_INVALID_ACTION = "Некорректное действие"
CB_NOT_FOUND = "Заявка не найдена"
CB_UNKNOWN_COMMAND = "Неизвестная команда"
CB_OPEN_HELP = "Открываю поддержку"

# User flow messages
ERR_MANAGER_GROUP_CONFIG = (
    "Не удалось создать обращение в группе менеджеров.\n"
    "Проверьте, что:\n"
    "1) указана именно forum-supergroup id в MANAGERS_GROUP_ID,\n"
    "2) в группе включены topics,\n"
    "3) бот добавлен в группу и имеет права администратора."
)
CB_MANAGER_GROUP_CONFIG_ERROR = "Ошибка настройки менеджерской группы"
SUPPORT_REQUEST_DETAILS = (
    "Пожалуйста, подробно опиши проблему в сообщении.\n"
    "Можно приложить фото или документ.\n\n"
    "Ответим в течение 24 часов."
)
CB_ACCEPTED = "Принято"
PRESENT_ALREADY_RECEIVED = "Если у вас еще остались вопросы, жмите на кнопку ниже"
PRESENT_PHONE_PROMPT = (
    "Пожалуйста, введи свой номер телефона, "
    "на него мы отправим бонус!\n\n"
    "Или нажми на кнопку «Поделиться номером»"
)
PHONE_CONFIRM_PROMPT = (
    "Проверь правильность номера телефона.\nНа него будет отправлен бонус\n\n{phone}"
)
PHONE_NOT_RECOGNIZED = (
    "Не могу распознать номер. Введи его в формате 79XXXXXXXXX "
    "или воспользуйся кнопкой поделиться контактом."
)
SESSION_NOT_FOUND_REVIEW = "Сессия подарка не найдена. Отправь /review."
PHONE_CONFIRMED = "Номер подтвержден"
PHONE_RETRY_PROMPT = "Хорошо, отправь номер еще раз."
PHONE_RETRY_CALLBACK = "Введи номер заново"
REVIEW_SCREENSHOT_PROMPT = (
    "Отлично! А теперь пришли, пожалуйста, скриншот твоего отзыва о товаре. "
    "Мы все проверим и пришлем подарок.\n\n"
    "Если отзыв еще не оставлен, то можно это сделать прямо сейчас 😉"
)
REVIEW_SCREENSHOT_REQUIRED = "Нужен скриншот отзыва (фото или изображение документом)."
REVIEW_TOPIC_CREATE_ERROR = (
    "Не удалось передать отзыв менеджеру (нет прав на создание топика).\n"
    "Напиши позже или обратись в саппорт бота"
)
REVIEW_SENT_THANKS = (
    "⚪️ Супер, спасибо!\n\n"
    "Скоро мы все проверим. Ответ поступит в этот бот — не останавливайте его"
)
REVIEW_SEND_RETRY = (
    "Не удалось передать отзыв менеджеру. Попробуй отправить скриншот еще раз чуть позже."
)
USE_START_HINT = "Используй /start для главного меню."

# Manager flow messages
MANAGER_REVIEW_ALREADY_REQUESTED = "Бот уже запросил у клиента отзыв, спасибо"
MANAGER_CB_ALREADY_SENT = "Запрос уже отправлялся"
MANAGER_CB_SENT_TO_CLIENT = "Клиенту отправлен запрос на отзыв"
MANAGER_CB_DONE = "Готово, клиент уведомлен"
MANAGER_CB_REJECTED = "Отклонено"
MANAGER_CB_ALREADY_PROCESSED = "Заявка уже обработана"
MANAGER_APPROVED_TOPIC = "Бот уведомил клиента о поступлении подарка, спасибо"
MANAGER_REJECTED_TOPIC = (
    "Отзыв отклонен. Клиент уведомлен и может отправить /review повторно."
)
CLIENT_REVIEW_REQUEST = (
    "{user_name}, рады, что удалось решить твой вопрос.\n\n"
    "У нас для тебя подарок за отзыв!\n\n"
    "Пожалуйста, введи свой номер телефона, "
    "на него мы отправим бонус!\n\n"
    "Или нажми на кнопку «Поделиться номером»"
)
CLIENT_SUPPORT_RESOLVED_ONLY = "{user_name}, рады, что удалось решить твой вопрос."
CLIENT_APPROVED = (
    "Подарок отправлен ✅\n\nСпасибо за отзыв! Начислили подарок на номер {phone}."
)
CLIENT_REJECTED = "К сожалению, не удалось подтвердить отзыв.\nМожно попробовать снова — отправь /review."

# Topic templates
SUPPORT_TOPIC_TITLE = "{user_name} (Вопрос продавцу)"
REVIEW_TOPIC_TITLE = "{user_name} (Отзыв)"
SUPPORT_TOPIC_GREETING = (
    "Новое обращение\n"
    "Пользователь: {user_name}\n"
    "Категория: {category}\n\n"
    "Пишите в этот топик — бот доставит ответ клиенту.\n"
    "Когда проблема будет решена, можно нажать на кнопку, чтобы запросить у клиента отзыв"
)
REVIEW_TOPIC_CAPTION = (
    "Нужно проверить отзыв и начислить бонус.\n"
    "Пользователь: {user_name}\n"
    "Телефон: {phone}"
)
