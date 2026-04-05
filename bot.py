import asyncio
import json
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CONTENT_FILE = Path("content/blocks_ru.json")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Create .env from .env.example and add your token.")

if not CONTENT_FILE.exists():
    raise RuntimeError(f"Content file not found: {CONTENT_FILE}")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

with CONTENT_FILE.open("r", encoding="utf-8") as f:
    BLOCKS = json.load(f)

BLOCKS_BY_ID = {block["id"]: block for block in BLOCKS}

SECTION_TITLES = {
    "overview": "Обзор",
    "indications": "Показания",
    "contraindications": "Противопоказания",
    "anatomy": "Анатомия",
    "positioning": "Положение пациента и датчика",
    "goal": "Цель блока",
    "technique": "Техника",
    "tips": "Практические советы",
    "complications": "Осложнения",
    "local_anesthetic": "Объём местного анестетика",
}

NYSORA_ARCHITECTURE_ORDER = [
    "overview",
    "indications",
    "contraindications",
    "anatomy",
    "positioning",
    "goal",
    "technique",
    "tips",
    "complications",
    "local_anesthetic",
]

DETAIL_LEVELS = {
    "basic": "Базовый",
    "standard": "Стандартный",
    "advanced": "Продвинутый",
}

DEFAULT_DETAIL_LEVEL = "standard"
USER_DETAIL_LEVEL: dict[int, str] = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_user_level(user_id: int) -> str:
    return USER_DETAIL_LEVEL.get(user_id, DEFAULT_DETAIL_LEVEL)


def user_level_suffix(user_id: int) -> str:
    level = get_user_level(user_id)
    return f"Текущий уровень детализации: <b>{DETAIL_LEVELS[level]}</b>."


def main_menu(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧭 Каталог блоков", callback_data="catalog")],
            [InlineKeyboardButton(text="🎚 Уровень детализации", callback_data="detail_menu")],
            [InlineKeyboardButton(text="📚 Архитектура NYSORA", callback_data="nysora_arch")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
        ]
    )


def detail_level_menu(current_level: str) -> InlineKeyboardMarkup:
    rows = []
    for level, title in DETAIL_LEVELS.items():
        marker = "✅ " if level == current_level else ""
        rows.append([InlineKeyboardButton(text=f"{marker}{title}", callback_data=f"detail:{level}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=block["title"], callback_data=f"block:{block['id']}")]
        for block in BLOCKS
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def block_menu(block_id: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=SECTION_TITLES[key], callback_data=f"section:{block_id}:{key}")]
        for key in NYSORA_ARCHITECTURE_ORDER
    ]
    rows.extend(
        [
            [InlineKeyboardButton(text="🖼 Фото", callback_data=f"photos:{block_id}")],
            [InlineKeyboardButton(text="🎬 Видео", callback_data=f"videos:{block_id}")],
            [InlineKeyboardButton(text="⬅️ К каталогу", callback_data="catalog")],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def level_adapt_list(items: list[str], detail_level: str) -> list[str]:
    if detail_level == "basic":
        return items[:1]
    if detail_level == "standard":
        return items[:2] if len(items) > 2 else items
    return items


def format_list(items: list[str]) -> str:
    return "\n".join(f"• {item}" for item in items)


def format_section(block: dict, section_key: str, detail_level: str) -> str:
    section_title = SECTION_TITLES[section_key]
    value = block.get(section_key)

    if isinstance(value, list):
        body = format_list(level_adapt_list(value, detail_level))
    else:
        body = str(value)

    text = f"<b>{block['title']}</b>\n\n<b>{section_title}</b>\n{body}"

    if detail_level == "advanced":
        pearls = block.get("expert_pearls", [])
        if pearls:
            text += "\n\n<b>Экспертные акценты</b>\n" + format_list(pearls)

    return text


def format_links(title: str, links: list[str]) -> str:
    lines = [f"<b>{title}</b>"]
    for idx, link in enumerate(links, start=1):
        lines.append(f"{idx}. {link}")
    return "\n".join(lines)


@dp.message(CommandStart())
async def command_start(message: Message) -> None:
    await message.answer(
        "Привет! Это справочник по регионарной анестезии под УЗИ для анестезиологов и реаниматологов.\n"
        "Структура материалов повторяет архитектуру NYSORA Nerve Blocks.\n\n"
        f"{user_level_suffix(message.from_user.id)}",
        reply_markup=main_menu(message.from_user.id),
    )


@dp.callback_query(F.data == "menu")
async def on_menu(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    await callback.message.edit_text(
        f"Главное меню.\n\n{user_level_suffix(user_id)}",
        reply_markup=main_menu(user_id),
    )
    await callback.answer()


@dp.callback_query(F.data == "detail_menu")
async def on_detail_menu(callback: CallbackQuery) -> None:
    current = get_user_level(callback.from_user.id)
    await callback.message.edit_text(
        "Выберите уровень детализации материалов:",
        reply_markup=detail_level_menu(current),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("detail:"))
async def on_detail_change(callback: CallbackQuery) -> None:
    level = callback.data.split(":", maxsplit=1)[1]
    user_id = callback.from_user.id

    if level not in DETAIL_LEVELS:
        await callback.answer("Неизвестный уровень", show_alert=True)
        return

    USER_DETAIL_LEVEL[user_id] = level
    await callback.message.edit_text(
        f"Уровень изменён на: <b>{DETAIL_LEVELS[level]}</b>",
        reply_markup=detail_level_menu(level),
    )
    await callback.answer("Сохранено")


@dp.callback_query(F.data == "about")
async def on_about(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "<b>О боте</b>\n"
        "Русскоязычный справочник по блокам под УЗ-навигацией.\n"
        "Аудитория: анестезиологи и реаниматологи.\n"
        "Контент организован по архитектуре NYSORA Nerve Blocks.\n"
        "Поддерживаются уровни детализации: базовый, стандартный, продвинутый.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu")]]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "nysora_arch")
async def on_nysora_arch(callback: CallbackQuery) -> None:
    architecture_text = "\n".join(
        f"• {SECTION_TITLES[key]}" for key in NYSORA_ARCHITECTURE_ORDER
    )
    await callback.message.edit_text(
        "<b>Архитектура карточки блока (NYSORA-style)</b>\n\n"
        f"{architecture_text}\n\n"
        "Дополнительно: фото- и видео-материалы.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🧭 Перейти к каталогу", callback_data="catalog")],
                [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu")],
            ]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "catalog")
async def on_catalog(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Выберите нужный блок:", reply_markup=catalog_menu())
    await callback.answer()


@dp.callback_query(F.data.startswith("block:"))
async def on_block(callback: CallbackQuery) -> None:
    block_id = callback.data.split(":", maxsplit=1)[1]
    block = BLOCKS_BY_ID.get(block_id)

    if not block:
        await callback.answer("Блок не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{block['title']}</b>\nВыберите раздел карточки:",
        reply_markup=block_menu(block_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("section:"))
async def on_section(callback: CallbackQuery) -> None:
    _, block_id, section_key = callback.data.split(":", maxsplit=2)
    block = BLOCKS_BY_ID.get(block_id)

    if not block or section_key not in SECTION_TITLES:
        await callback.answer("Раздел не найден", show_alert=True)
        return

    detail_level = get_user_level(callback.from_user.id)
    await callback.message.edit_text(
        format_section(block, section_key, detail_level),
        reply_markup=block_menu(block_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("photos:"))
async def on_block_photos(callback: CallbackQuery) -> None:
    block_id = callback.data.split(":", maxsplit=1)[1]
    block = BLOCKS_BY_ID.get(block_id)

    if not block:
        await callback.answer("Материал не найден", show_alert=True)
        return

    await callback.message.edit_text(
        format_links(f"Фото-материалы: {block['title']}", block["photos"]),
        reply_markup=block_menu(block_id),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("videos:"))
async def on_block_videos(callback: CallbackQuery) -> None:
    block_id = callback.data.split(":", maxsplit=1)[1]
    block = BLOCKS_BY_ID.get(block_id)

    if not block:
        await callback.answer("Материал не найден", show_alert=True)
        return

    await callback.message.edit_text(
        format_links(f"Видео-материалы: {block['title']}", block["videos"]),
        reply_markup=block_menu(block_id),
    )
    await callback.answer()


@dp.message()
async def fallback(message: Message) -> None:
    await message.answer("Нажмите /start, чтобы открыть каталог блоков.")


async def main() -> None:
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
