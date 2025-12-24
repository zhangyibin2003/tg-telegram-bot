import logging
import json
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# ================= 配置区域 =================
BOT_TOKEN = "8440135512:AAE_5hnHEJhPO7fCjvl9-7zOIxW7HTxUCrE"  # <--- 记得填回你的 Token
MEMBERS = ["Nicole", "Kristin", "XZ", "Wish", "Veil", "三三"]
DATA_FILE = "score_data.json"

# ================= 代码逻辑 =================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def load_data():
    if not os.path.exists(DATA_FILE):
        initial_data = {name: {"today": 0, "total": 0} for name in MEMBERS}
        save_data(initial_data)
        return initial_data
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def generate_scoreboard_text(data):
    """生成实时更新的记分牌文本"""
    # 按今日分数排序
    sorted_items = sorted(data.items(), key=lambda x: x[1]['today'], reverse=True)

    # 获取当前时间
    now_time = datetime.datetime.now().strftime("%H:%M:%S")

    text = "🏆 **实时积分排行榜** 🏆\n"
    text += f"🕒 更新时间: {now_time}\n"
    text += "━━━━━━━━━━━━━━━━━━\n"
    text += "   **成员** **今日** **累计**\n"

    # 奖牌图标
    medals = ["🥇", "🥈", "🥉"]

    for idx, (name, scores) in enumerate(sorted_items):
        rank = medals[idx] if idx < 3 else "▫️"
        today = scores['today']
        total = scores['total']

        # 格式化对齐：名字左对齐，分数居中
        # 这种排版在手机上效果最好
        text += f"{rank} `{name:<7}` :  `{today:>2}`   |  `{total:>3}`\n"

    text += "━━━━━━━━━━━━━━━━━━\n"
    text += "👇 点击下方按钮加分"
    return text

def get_main_keyboard():
    """获取主打分键盘"""
    keyboard = []
    row = []
    for member in MEMBERS:
        row.append(InlineKeyboardButton(f"{member} +1", callback_data=f"add_{member}"))
        if len(row) == 2: # 每行2个
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # 添加管理按钮
    keyboard.append([InlineKeyboardButton("⚙️ 管理面板 / 清零", callback_data="admin_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    """获取管理键盘"""
    keyboard = [
        [InlineKeyboardButton("🌅 开启新的一天 (清零今日)", callback_data="reset_today_confirm")],
        [InlineKeyboardButton("🧨 重置所有数据 (慎用)", callback_data="reset_all_confirm")],
        [InlineKeyboardButton("🔙 返回打分", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 核心交互 ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """发送并置顶记分牌"""
    data = load_data()
    text = generate_scoreboard_text(data)
    markup = get_main_keyboard()

    # 发送新消息
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=markup,
        parse_mode='Markdown'
    )

    # 尝试置顶消息 (需要管理员权限)
    try:
        await context.bot.pin_chat_message(chat_id=update.effective_chat.id, message_id=msg.message_id)
    except Exception as e:
        print(f"置顶失败 (可能没有权限): {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理所有按钮点击"""
    query = update.callback_query
    data_key = query.data
    scores = load_data()

    # 1. 加分逻辑
    if data_key.startswith("add_"):
        name = data_key.split("_")[1]
        if name in scores:
            scores[name]['today'] += 1
            scores[name]['total'] += 1
            save_data(scores)

            # 关键：直接修改原消息的文本，实现实时刷新
            new_text = generate_scoreboard_text(scores)
            try:
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
            except Exception:
                pass # 如果内容没变（极少情况），忽略报错

            await query.answer(f"✅ {name} +1 分！", show_alert=False)
        else:
            await query.answer("❌ 成员不存在")

    # 2. 进入管理菜单
    elif data_key == "admin_menu":
        await query.edit_message_reply_markup(reply_markup=get_admin_keyboard())
        await query.answer()

    # 3. 返回主菜单
    elif data_key == "back_to_main":
        await query.edit_message_reply_markup(reply_markup=get_main_keyboard())
        await query.answer()

    # 4. 确认清零今日
    elif data_key == "reset_today_confirm":
        # 执行清零今日
        for name in scores:
            scores[name]['today'] = 0
        save_data(scores)

        # 刷新界面
        new_text = generate_scoreboard_text(scores)
        await query.edit_message_text(text=new_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        await query.answer("🌅 新的一天开始了！今日积分已归零。", show_alert=True)

    # 5. 确认清零所有
    elif data_key == "reset_all_confirm":
        # 二次确认逻辑可以用多层菜单实现，这里为了便捷直接执行，但弹窗警告
        for name in scores:
            scores[name]['today'] = 0
            scores[name]['total'] = 0
        save_data(scores)

        new_text = generate_scoreboard_text(scores)
        await query.edit_message_text(text=new_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
        await query.answer("🧨 所有数据已销毁！一切重新开始。", show_alert=True)

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 2.0 实时面板机器人正在运行...")
    application.run_polling()
