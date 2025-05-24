import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackContext
)
import httpx

# تكوين التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بيانات البوت
TOKEN = "7711567780:AAEs4rEZA7d8f2WeBLcRW3rpG5Kita8ZCbA"
ADMIN_CHAT_ID = "6100378097"

# روابط API لشحن كل فئة
PUBG_CHARGE_API = {
    "1": {  # 60 UC
        "url": "https://your-api.com/charge-60uc",
        "method": "POST",
        "api_key": "your_api_key_here"
    },
    "2": {  # 325 UC
        "url": "https://your-api.com/charge-325uc",
        "method": "POST",
        "api_key": "your_api_key_here"
    },
    "3": {  # 660 UC
        "url": "https://your-api.com/charge-660uc",
        "method": "POST",
        "api_key": "your_api_key_here"
    },
    "4": {  # 1800 UC
        "url": "https://your-api.com/charge-1800uc",
        "method": "POST",
        "api_key": "your_api_key_here"
    }
}

# تخزين البيانات
user_balances = {}
payment_requests = {}
game_charges = {
    "pubg": {
        "name": "ببجي موبايل",
        "options": {
            "1": {"name": "60 UC", "price": 10000},
            "2": {"name": "325 UC", "price": 50000},
            "3": {"name": "660 UC", "price": 100000},
            "4": {"name": "1800 UC", "price": 250000},
        }
    }
}

def is_admin(user_id: str) -> bool:
    return user_id == ADMIN_CHAT_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("الدعم الفني", callback_data='support')],
        [InlineKeyboardButton("شحن ألعاب", callback_data='charge_games')],
        [InlineKeyboardButton("شحن تطبيقات", callback_data='charge_apps')],
        [InlineKeyboardButton("رصيدي", callback_data='my_balance')],
        [InlineKeyboardButton("شحن رصيد", callback_data='charge_balance')],
    ]
    
    if is_admin(str(update.effective_user.id)):
        keyboard.append([InlineKeyboardButton("لوحة المسؤول", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
    🏪 *مرحباً بك في بوت الخدمات الإلكترونية* 🏪
    
    *الخدمات المتاحة:*
    - شحن رصيد ألعاب مثل ببجي موبايل
    - شحن رصيد تطبيقات
    - دعم فني على مدار الساعة
    
    اختر الخدمة التي تريدها من الأزرار أدناه 👇
    """
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    support_message = """
    📞 *الدعم الفني*
    
    للتواصل مع المسؤول، يرجى الضغط على الرابط أدناه:
    @lordstoreadmin
    """
    await query.edit_message_text(support_message, parse_mode='Markdown')

async def charge_games(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("ببجي موبايل", callback_data='game_pubg')],
        [InlineKeyboardButton("العودة", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("🎮 *اختر اللعبة التي تريد شحن رصيد لها:*", reply_markup=reply_markup, parse_mode='Markdown')

async def charge_apps(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.edit_message_text("⏳ *قريباً سيتم إضافة خدمة شحن التطبيقات*", parse_mode='Markdown')

async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = str(query.from_user.id)
    balance = user_balances.get(user_id, 0)
    await query.edit_message_text(f"💰 *رصيدك الحالي:* {balance} ليرة سورية", parse_mode='Markdown')

async def charge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "💳 *طريقة الإيداع*\n\n"
        "1. أرسل المبلغ المراد إيداعه (رقم فقط)\n"
        "مثال: 10000\n\n"
        "الحد الأدنى للإيداع: 10,000 ليرة",
        parse_mode='Markdown'
    )
    
    context.user_data['deposit_step'] = 'waiting_for_amount'

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("طلبات الإيداع", callback_data='deposit_requests')],
        [InlineKeyboardButton("رجوع", callback_data='back')]
    ]
    
    await query.edit_message_text(
        "👑 لوحة التحكم - المسؤول\n\nاختر الإجراء المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_deposit_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(str(query.from_user.id)):
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول!")
        return
    
    if not payment_requests:
        await query.edit_message_text("⚠️ لا توجد طلبات إيداع معلقة")
        return
    
    buttons = []
    for user_id, request_data in payment_requests.items():
        buttons.append([
            InlineKeyboardButton(
                f"طلب {user_id} - {request_data.get('amount', 0)} ليرة",
                callback_data=f"view_request_{user_id}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("رجوع", callback_data="admin_panel")])
    
    await query.edit_message_text(
        "📋 طلبات الإيداع المعلقة:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def view_deposit_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split('_')[-1]
    request_data = payment_requests.get(user_id, {})
    trans_id = request_data.get('transaction_id')
    amount = request_data.get('amount')
    
    if not trans_id:
        await query.edit_message_text("⚠️ الطلب لم يعد موجوداً")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
        ],
        [InlineKeyboardButton("رجوع", callback_data="deposit_requests")]
    ]
    
    message = f"""
📄 تفاصيل الطلب:
👤 المستخدم: {user_id}
💳 رقم التحويل: {trans_id}
💰 المبلغ: {amount} ليرة
    """
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
async def accept_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split('_')[-1]
    request_data = payment_requests.pop(user_id, {})
    trans_id = request_data.get('transaction_id')
    amount = request_data.get('amount')
    
    if not trans_id:
        await query.edit_message_text("⚠️ الطلب لم يعد موجوداً")
        return
    
    user_balances[user_id] = user_balances.get(user_id, 0) + amount
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ تم قبول طلب الإيداع الخاص بك\nتم إضافة {amount} ليرة إلى رصيدك"
    )
    
    await query.edit_message_text(
        f"تمت الموافقة على طلب المستخدم {user_id}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع", callback_data="deposit_requests")]
        ])
    )

async def reject_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.data.split('_')[-1]
    request_data = payment_requests.pop(user_id, {})
    trans_id = request_data.get('transaction_id')
    amount = request_data.get('amount')
    
    if not trans_id:
        await query.edit_message_text("⚠️ الطلب لم يعد موجوداً")
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"❌ تم رفض طلب الإيداع الخاص بك\nيرجى التواصل مع الدعم الفني")
    
    await query.edit_message_text(
        f"تم رفض طلب المستخدم {user_id}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("رجوع", callback_data="deposit_requests")]
        ])
    )

async def handle_game_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    game = query.data.split('_')[1]
    
    if game == 'pubg':
        keyboard = [
            [InlineKeyboardButton(f"60 UC - 10000 ليرة", callback_data='pubg_option_1')],
            [InlineKeyboardButton(f"325 UC - 50000 ليرة", callback_data='pubg_option_2')],
            [InlineKeyboardButton(f"660 UC - 100000 ليرة", callback_data='pubg_option_3')],
            [InlineKeyboardButton(f"1800 UC - 250000 ليرة", callback_data='pubg_option_4')],
            [InlineKeyboardButton("العودة", callback_data='charge_games')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🎮 *ببجي موبايل - اختر الفئة:*", reply_markup=reply_markup, parse_mode='Markdown')

async def handle_pubg_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    option = query.data.split('_')[-1]
    game_data = game_charges['pubg']['options'][option]
    
    context.user_data['selected_game'] = 'pubg'
    context.user_data['selected_option'] = option
    context.user_data['charge_price'] = game_data['price']
    
    await query.edit_message_text(f"✏️ يرجى إرسال ID اللعبة (رقم اللاعب) لشحن {game_data['name']} بقيمة {game_data['price']} ليرة سورية:")
    context.user_data['expecting'] = 'game_id'

async def handle_game_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_id = str(update.message.from_user.id)
    game_id = update.message.text.strip()
    
    if not game_id.isdigit():
        await update.message.reply_text("⚠️ يُرجى إدخال **رقم اللاعب** صحيح (أرقام فقط).", parse_mode="Markdown")
        return
    
    # بيانات الفئة المختارة
    option = user_data['selected_option']
    api_config = PUBG_CHARGE_API.get(option)
    
    if not api_config:
        await update.message.reply_text("❌ حدث خطأ في النظام، يرجى المحاولة لاحقًا.")
        return
    
    # التحقق من رصيد المستخدم
    charge_price = user_data['charge_price']
    if user_balances.get(user_id, 0) < charge_price:
        await update.message.reply_text("❌ رصيدك غير كافي! يرجى شحن الرصيد أولاً.")
        return
    
    # إرسال طلب الشحن إلى API
    try:
        async with httpx.AsyncClient() as client:
            # إعداد بيانات الطلب
            data = {
                "player_id": game_id,
                "user_id": user_id,
                "api_key": api_config["api_key"]
            }
            
            # إرسال الطلب
            if api_config["method"] == "POST":
                response = await client.post(api_config["url"], json=data, timeout=30)
            else:
                response = await client.get(api_config["url"], params=data, timeout=30)
            
            # معالجة الرد
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    # خصم المبلغ من رصيد المستخدم
                    user_balances[user_id] -= charge_price
                    
                    await update.message.reply_text(
                        f"✅ تم الشحن بنجاح!\n\n"
                        f"• اللعبة: ببجي موبايل\n"
                        f"• الكمية: {result.get('amount', '60 UC')}\n"
                        f"• رقم العملية: `{result.get('transaction_id', 'N/A')}`\n\n"
                        f"تم خصم {charge_price} ليرة من رصيدك",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text(f"❌ فشل الشحن: {result.get('message', 'خطأ غير معروف')}")
            else:
                await update.message.reply_text("⚠️ تعذر الاتصال بخادم الشحن، يرجى المحاولة لاحقًا.")
    
    except httpx.TimeoutException:
        await update.message.reply_text("⏳ انتهى وقت الانتظار، يرجى المحاولة لاحقًا.")
    except Exception as e:
        logger.error(f"فشل الاتصال بالـ API: {str(e)}")
        await update.message.reply_text("🔴 حدث خطأ تقني، يرجى إعلام الدعم.")
    
    # مسح البيانات المؤقتة
    user_data.clear()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == 'support':
        await support(update, context)
    elif query.data == 'charge_games':
        await charge_games(update, context)
    elif query.data == 'charge_apps':
        await charge_apps(update, context)
    elif query.data == 'my_balance':
        await my_balance(update, context)
    elif query.data == 'charge_balance':
        await charge_balance(update, context)
    elif query.data == 'admin_panel':
        await admin_panel(update, context)
    elif query.data == 'deposit_requests':
        await handle_deposit_requests(update, context)
    elif query.data.startswith('view_request_'):
        await view_deposit_request(update, context)
    elif query.data.startswith('accept_'):
        await accept_deposit(update, context)
    elif query.data.startswith('reject_'):
        await reject_deposit(update, context)
    elif query.data.startswith('game_'):
        await handle_game_selection(update, context)
    elif query.data.startswith('pubg_option_'):
        await handle_pubg_option(update, context)
    elif query.data == 'back':
        await start(update, context)
        
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    user_id = str(update.message.from_user.id)
    
    if 'deposit_step' in user_data:
        if user_data['deposit_step'] == 'waiting_for_amount':
            try:
                amount = int(update.message.text)
                
                if amount < 10000:
                    await update.message.reply_text("⚠️ الحد الأدنى للإيداع 10,000 ليرة")
                    return
                
                user_data['deposit_amount'] = amount
                user_data['deposit_step'] = 'waiting_for_transaction_id'
                
                await update.message.reply_text(
                    f"📌 تم استلام المبلغ: {amount} ليرة\n\n"
                    "الآن أرسل رقم العملية (رقم التحويل)\n"
                    "مثال: SY123456",
                    parse_mode='Markdown'
                )
                
            except ValueError:
                await update.message.reply_text("⚠️ يرجى إرسال المبلغ كرقم فقط (بدون أحرف أو رموز)")
        
        elif user_data['deposit_step'] == 'waiting_for_transaction_id':
            transaction_id = update.message.text.strip()
            
            if not transaction_id:
                await update.message.reply_text("⚠️ يرجى إرسال رقم العملية صحيح")
                return
                
            amount = user_data['deposit_amount']
            
            # حفظ طلب الإيداع
            payment_requests[user_id] = {
                'amount': amount,
                'transaction_id': transaction_id,
                'status': 'pending'
            }
            
            # إرسال تأكيد للمستخدم
            await update.message.reply_text(
                f"✅ تم استلام طلب الإيداع\n\n"
                f"المبلغ: {amount} ليرة\n"
                f"رقم العملية: {transaction_id}\n\n"
                "سيتم مراجعة الطلب من قبل المسؤول",
                parse_mode='Markdown'
            )
            
            # إرسال إشعار للمسؤول
            admin_msg = (
                f"📬 طلب إيداع جديد\n\n"
                f"👤 المستخدم: {user_id}\n"
                f"💳 المبلغ: {amount} ليرة\n"
                f"🆔 رقم العملية: {transaction_id}"
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
                        InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
                    ],
                    [InlineKeyboardButton("عرض الطلبات", callback_data="deposit_requests")]
                ])
            )
            
            # مسح بيانات الجلسة
            user_data.clear()
    
    elif user_data.get('expecting') == 'game_id':
        await handle_game_id(update, context)

async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) == ADMIN_CHAT_ID:
        command = update.message.text.split('_')
        if len(command) == 2 and command[0] == '/approve':
            user_id = command[1]
            amount = 10000
            user_balances[user_id] = user_balances.get(user_id, 0) + amount
            await context.bot.send_message(chat_id=user_id, text=f"✅ تمت الموافقة على طلبك وتم إضافة {amount} ليرة سورية إلى رصيدك")
            await update.message.reply_text(f"تمت الموافقة على طلب المستخدم {user_id}")

async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) == ADMIN_CHAT_ID:
        command = update.message.text.split('_')
        if len(command) == 2 and command[0] == '/cancel':
            user_id = command[1]
            await context.bot.send_message(chat_id=user_id, text="❌ تم رفض طلب شحن الرصيد، يرجى التواصل مع الدعم الفني")
            await update.message.reply_text(f"تم رفض طلب المستخدم {user_id}")

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("approve", approve_request))
    application.add_handler(CommandHandler("cancel", cancel_request))

    application.run_polling()

if __name__ == '__main__':
    main()