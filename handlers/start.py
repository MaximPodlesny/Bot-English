from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from db.create_tables import get_db
from handlers.utils import new_user
# from handlers.utils.admins import ADMINS
# from handlers.utils.record_history_by_user_id import record_history_by_user_id



router = Router()


@router.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    """Обработчик команды /start."""

    # Приветствие
    await message.answer("Забудьте о зубрежке! Учите английские слова легко и эффективно с помощью нашего бота! \
\
Хотите свободно говорить по-английски?  Тогда вам нужно знать много слов! Но как запомнить их все?  \
\
Наш бот использует научный подход к обучению, основанный на системе Spaced Repetition (SR).  Это значит, что вы будете повторять слова в оптимальные моменты, чтобы закрепить их в памяти надолго. \
\
Вот как это работает:\
\
* Удобные порции:  Выбирайте, сколько слов вы хотите учить за раз (от 10 до 100). \
* Гибкий график:  Настраивайте интервалы между подачей новых порций слов (от 1 до 3 дней).\
* Оптимальные повторения:  Бот автоматически напомнит вам о повторении слов в нужное время: \
    * Первое повторение:  через час\
    * Второе повторение:  через 5 часов\
    * Третье повторение:  через 24 часа\
    * Четвертое повторение:  через 4 дня\
    * Пятое повторение:  через 14 дней\
    * Шестое повторение:  через 30 дней\
    * Далее:  раз в 30 дней\
\
Почему такой подход работает?\
\
* Научно доказано:  Система SR основана на принципах кривой забывания Эббингауза, которая показывает, как быстро мы забываем информацию.  \
* Эффективность:  Повторение слов в оптимальные моменты помогает закрепить их в долговременной памяти.\
* Экономия времени:  Вы учите слова более эффективно, тратя меньше времени на зубрежку.")
                         
    # Запись нового пользователя
    await new_user(message.from_user.id)

    builder = InlineKeyboardBuilder()
    builder.button(text="Новые слова", callback_data="new_words")
    builder.button(text="Повторение", callback_data="repeat_words")
    builder.button(text="Настройки", callback_data="settings")
    await message.answer(
        "Привет! Выбери действие:",
        reply_markup=builder.as_markup()
    )
    # if message.from_user.id in ADMINS:
    #     pass
    # else:
    #     if ' ' in message.text:
    #         pass
    #     else:
    #         pass
