import peewee
import os
from dotenv import load_dotenv

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards.phoneKeyboard import get_phone_keyboard
from keyboards.roomTypeKeyboard import room_type_keyboard
from keyboards.repairClassKeyboard import repair_class_keyboard
from keyboards.createOrderKeyboard import create_order_keyboard
from keyboards.propertyTypeKeyboard import type_of_property_keyboard

from states import OrderConfigure

from dataBase.models.UserModel import UserModel
from dataBase.models.OrderModel import OrderModel
from dataBase.models.RoomTypeModel import RoomTypeModel
from dataBase.models.PropertyTypesModel import PropertyTypeModel
from dataBase.models.RepairClassesModel import RepairClassModel

from misc.consts import *
from misc.utils import phone_parse, cost_calculator

router = Router()

load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))


@router.message(Command("start"))
@router.message(F.text == CREATE_ORDER)
async def start(message: Message, state: FSMContext):
    await message.answer("Какой у вас тип недвижимости?",
                         reply_markup=type_of_property_keyboard())
    await state.set_state(OrderConfigure.square)


@router.message(F.text,
                OrderConfigure.square)
async def square(message: Message, state: FSMContext):
    await state.update_data(name=message.chat.first_name,
                            chat_id=message.chat.id,
                            property_type=message.text,
                            user=message.from_user.username)
    await message.answer("Какая площадь помещения?")
    await state.set_state(OrderConfigure.room_type)


@router.message(F.text,
                OrderConfigure.room_type)
async def room_type(message: Message, state: FSMContext):
    try:
        room_square = float(message.text.replace(',', '.').replace(' ', ''))
        if room_square % 1 == 0:
            room_square = int(room_square)
        await state.update_data(square=room_square)
        await state.set_state(OrderConfigure.repair_class)
        await message.answer("Какой у вас тип помещения?",
                             reply_markup=room_type_keyboard())
    except ValueError:
        await message.answer("Введите площадь в формате: 25.45 ")
        await state.set_state(OrderConfigure.room_type)


@router.message(F.text,
                OrderConfigure.repair_class)
async def repair_class(message: Message, state: FSMContext):
    await state.update_data(room_type=message.text)
    await message.answer("Какой класс ремонта вы планируете?",
                         reply_markup=repair_class_keyboard())
    await state.set_state(OrderConfigure.phone)


@router.message(F.text,
                OrderConfigure.phone)
async def phone(message: Message, state: FSMContext):
    await state.update_data(repair_class=message.text)
    await message.answer("Ваш расчет готов! На какой номер телефона в Telegram выслать стоимость?\n"
                         "Например: 79991807777\n"
                         "Или нажмите на кнопку ниже.",
                         reply_markup=get_phone_keyboard())
    await state.set_state(OrderConfigure.confirm)


@router.message(OrderConfigure.confirm)
async def confirm(message: Message, state: FSMContext):
    await state.update_data(phone=phone_parse(message.text) if message.contact is None
    else phone_parse(message.contact.phone_number))

    data = await state.get_data()
    #
    try:
        user = await UserModel.aio_create(chat_id=data.get('chat_id'),
                                          first_name=data.get('name'),
                                          phone_number=data.get('phone'))
    except peewee.IntegrityError:
        user = await UserModel.aio_get(UserModel.chat_id == data.get('chat_id'))

    property_type = await PropertyTypeModel.aio_get(PropertyTypeModel.name == data.get('property_type'))
    room_type = await RoomTypeModel.aio_get(RoomTypeModel.name == data.get('room_type'))
    repair_class = await RepairClassModel.aio_get(RepairClassModel.name == data.get('repair_class'))

    order = await OrderModel.aio_create(user_id=user,
                                        property_type=property_type,
                                        square=float(data.get('square')),
                                        room_type=room_type,
                                        repair_class=repair_class,
                                        cost=cost_calculator(data))
    #

    await bot.send_message(chat_id=os.getenv('TARGET_CHAT'), text=f"#Заказ_{order.id}\n"
                                                                  f"Тип недвижимости: {data.get('property_type')}\n"
                                                                  f"Площадь помещения: {data.get('square')}\n"
                                                                  f"Тип помещения: {data.get('room_type')}\n"
                                                                  f"Класс ремонта: {data.get('repair_class')}\n"
                                                                  f"Номер телефона для связи: +7{data.get('phone')}\n"
                                                                  f"Стоимость ремонта: от {cost_calculator(data)} руб.\n"
                                                                  f"@{data.get('user')}")

    await message.answer(f"Тип недвижимости: {data.get('property_type')}\n"
                         f"Площадь помещения: {data.get('square')}\n"
                         f"Тип помещения: {data.get('room_type')}\n"
                         f"Класс ремонта: {data.get('repair_class')}\n"
                         f"Номер телефона для связи: +7{data.get('phone')}\n"
                         f"Стоимость ремонта: от {cost_calculator(data)} руб.")

    await message.answer("Заявка отправлена! Ожидайте обратную связь)\n"
                         "Если хотите оставить еще одну заявку, нажмите кнопку ниже",
                         reply_markup=create_order_keyboard())
    await state.clear()