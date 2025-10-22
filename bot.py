import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os
from collections import defaultdict

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DATA_FILE = 'finance_data.json'

class FinanceBot:
    def __init__(self):
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_data(self):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_group_data(self, chat_id):
        chat_id_str = str(chat_id)
        if chat_id_str not in self.data:
            self.data[chat_id_str] = {'records': []}
        return self.data[chat_id_str]
    
    def add_record(self, chat_id, user_name, amount, type_name, category, note):
        group_data = self.get_group_data(chat_id)
        record = {
            'id': len(group_data['records']) + 1,
            'user': user_name,
            'amount': amount,
            'type': type_name,
            'category': category,
            'note': note,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        group_data['records'].append(record)
        self.save_data()
        return record
    
    def get_stats(self, chat_id, start_date, end_date):
        group_data = self.get_group_data(chat_id)
        records = [r for r in group_data['records'] 
                  if start_date <= r['date'] <= end_date]
        
        total_income = sum(r['amount'] for r in records if r['type'] == 'income')
        total_expense = sum(r['amount'] for r in records if r['type'] == 'expense')
        balance = total_income - total_expense
        
        income_by_category = defaultdict(float)
        expense_by_category = defaultdict(float)
        
        for r in records:
            if r['type'] == 'income':
                income_by_category[r['category']] += r['amount']
            else:
                expense_by_category[r['category']] += r['amount']
        
        return {
            'total_income': total_income,
            'total_expense': total_expense,
            'balance': balance,
            'income_by_category': dict(income_by_category),
            'expense_by_category': dict(expense_by_category),
            'count': len(records)
        }

bot = FinanceBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
💰 欢迎使用进出款统计机器人！

📥 记录收入：
/in <金额> <分类> <备注>
例：/in 5000 工资 月薪

📤 记录支出：
/out <金额> <分类> <备注>
例：/out 200 餐饮 午餐

📊 查看统计：
/today - 今日统计
/week - 本周统计
/month - 本月统计
/list - 最近20条记录

💡 快捷记录：
+ 5000 工资 月薪
- 200 餐饮 午餐
"""
    await update.message.reply_text(welcome_text)

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("❌ 格式：/in <金额> <分类> <备注>")
            return
        
        amount = float(context.args[0])
        category = context.args[1]
        note = ' '.join(context.args[2:]) if len(context.args) > 2 else '无'
        
        user_name = update.message.from_user.full_name
        chat_id = update.message.chat_id
        
        record = bot.add_record(chat_id, user_name, amount, 'income', category, note)
        
        await update.message.reply_text(
            f"✅ 收入记录成功！\n\n"
            f"📝 #{record['id']} | +¥{amount:.2f}\n"
            f"📂 {category} | {note}\n"
            f"👤 {user_name} | {record['time']}"
        )
    except ValueError:
        await update.message.reply_text("❌ 金额格式错误！")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ 操作失败")

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("❌ 格式：/out <金额> <分类> <备注>")
            return
        
        amount = float(context.args[0])
        category = context.args[1]
        note = ' '.join(context.args[2:]) if len(context.args) > 2 else '无'
        
        user_name = update.message.from_user.full_name
        chat_id = update.message.chat_id
        
        record = bot.add_record(chat_id, user_name, amount, 'expense', category, note)
        
        await update.message.reply_text(
            f"✅ 支出记录成功！\n\n"
            f"📝 #{record['id']} | -¥{amount:.2f}\n"
            f"📂 {category} | {note}\n"
            f"👤 {user_name} | {record['time']}"
        )
    except ValueError:
        await update.message.reply_text("❌ 金额格式错误！")
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ 操作失败")

async def today_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    today = datetime.now().strftime('%Y-%m-%d')
    stats = bot.get_stats(chat_id, today, today)
    
    response = f"📊 今日统计 ({today})\n\n"
    response += f"💵 收入：¥{stats['total_income']:.2f}\n"
    response += f"💸 支出：¥{stats['total_expense']:.2f}\n"
    response += f"💰 净额：¥{stats['balance']:.2f}\n"
    response += f"📝 记录：{stats['count']}笔\n"
    
    if stats['income_by_category']:
        response += "\n📥 收入明细：\n"
        for cat, amt in stats['income_by_category'].items():
            response += f"  • {cat}：¥{amt:.2f}\n"
    
    if stats['expense_by_category']:
        response += "\n📤 支出明细：\n"
        for cat, amt in stats['expense_by_category'].items():
            response += f"  • {cat}：¥{amt:.2f}\n"
    
    await update.message.reply_text(response)

async def week_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    today = datetime.now()
    start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    stats = bot.get_stats(chat_id, start, end)
    
    response = f"📊 本周统计 ({start}~{end})\n\n"
    response += f"💵 收入：¥{stats['total_income']:.2f}\n"
    response += f"💸 支出：¥{stats['total_expense']:.2f}\n"
    response += f"💰 净额：¥{stats['balance']:.2f}\n"
    
    await update.message.reply_text(response)

async def month_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    today = datetime.now()
    start = today.replace(day=1).strftime('%Y-%m-%d')
    end = today.strftime('%Y-%m-%d')
    stats = bot.get_stats(chat_id, start, end)
    
    response = f"📊 本月统计 ({start}~{end})\n\n"
    response += f"💵 收入：¥{stats['total_income']:.2f}\n"
    response += f"💸 支出：¥{stats['total_expense']:.2f}\n"
    response += f"💰 净额：¥{stats['balance']:.2f}\n"
    
    await update.message.reply_text(response)

async def list_records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    group_data = bot.get_group_data(chat_id)
    records = group_data['records']
    
    if not records:
        await update.message.reply_text("📭 暂无记录")
        return
    
    recent = records[-20:][::-1]
    response = "📋 最近20条记录：\n\n"
    
    for r in recent:
        icon = "📥" if r['type'] == 'income' else "📤"
        sign = "+" if r['type'] == 'income' else "-"
        response += f"{icon} #{r['id']} {sign}¥{r['amount']:.2f}\n"
        response += f"   {r['category']} | {r['note']}\n"
        response += f"   {r['date']} {r['time']}\n\n"
    
    await update.message.reply_text(response)

async def quick_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if not (text.startswith('+') or text.startswith('-')):
        return
    
    try:
        parts = text[1:].strip().split(None, 2)
        if len(parts) < 2:
            return
        
        amount = float(parts[0])
        category = parts[1]
        note = parts[2] if len(parts) > 2 else '无'
        
        user_name = update.message.from_user.full_name
        chat_id = update.message.chat_id
        type_name = 'income' if text.startswith('+') else 'expense'
        
        record = bot.add_record(chat_id, user_name, amount, type_name, category, note)
        
        sign = "+" if type_name == 'income' else "-"
        await update.message.reply_text(
            f"✅ 记录成功！\n#{record['id']} | {sign}¥{amount:.2f}\n{category} | {note}"
        )
    except:
        pass

def main():
    TOKEN = os.environ.get('BOT_TOKEN', '8203006758:AAGXB0Ch12Szwz9t6GEmbLD8ygrf60-UqEM')
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("in", add_income))
    application.add_handler(CommandHandler("out", add_expense))
    application.add_handler(CommandHandler("today", today_stats))
    application.add_handler(CommandHandler("week", week_stats))
    application.add_handler(CommandHandler("month", month_stats))
    application.add_handler(CommandHandler("list", list_records))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, quick_record))
    
    logger.info("机器人启动成功！")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
