#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telebot
from telebot import types
import sqlite3
import time
import io
import os
import sys

# --- Configuration ---
TOKEN = "8426285729:AAHTDfAtrPeiTjXXi4EMm2VlsB0VmVtqLvI"
ADMIN_ID = 7128914520
BKASH_NO = "01615682337"
NAGAD_NO = "01615682337"

# --- Bot Initialization ---
bot = telebot.TeleBot(TOKEN)

# Temporary storage for pending orders
pending_orders = {}

# Get script directory for database path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, 'fb_id_sell.db')

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        description TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        account_data TEXT NOT NULL,
        sold INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS used_trx (
        trx_id TEXT PRIMARY KEY
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        trx_id TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    conn.commit()
    conn.close()
    print("✅ Database ready at:", DB_PATH)

init_db()

# --- Helpers ---
def get_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if user_id == ADMIN_ID:
        markup.add(
            types.KeyboardButton("🛠 Admin Panel"),
            types.KeyboardButton("📊 Statistics"),
            types.KeyboardButton("📦 Stock Status")
        )
    else:
        markup.add(
            types.KeyboardButton("🛒 Buy IDs"),
            types.KeyboardButton("👤 My Account"),
            types.KeyboardButton("📞 Support"),
            types.KeyboardButton("📜 My Orders")
        )
    return markup

def parse_account(account_data):
    """
    Supported formats:
      user:pass:cookie
      user:pass          (no cookie)
      user               (no pass, no cookie)
    """
    parts = account_data.split(':', 2)
    username = parts[0].strip() if len(parts) > 0 else "N/A"
    password = parts[1].strip() if len(parts) > 1 else "No Password"
    cookie   = parts[2].strip() if len(parts) > 2 else "No Cookie"
    return username, password, cookie

# ============= START =============
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome = (
        "🎉 *Welcome to FB ID Shop!*\n\n"
        "🔑 Buy real & verified Facebook IDs\n"
        "✅ Instant auto delivery\n"
        "💸 Best price guarantee\n"
        "📞 24/7 customer support\n\n"
        "Use the buttons below to get started!"
    )
    bot.send_message(message.chat.id, welcome,
                     parse_mode="Markdown",
                     reply_markup=get_main_menu(message.from_user.id))

# ============= USER SECTION =============

@bot.message_handler(func=lambda m: m.text == "👤 My Account")
def my_account(m):
    user = m.from_user
    text = (
        f"👤 *Your Profile*\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"📝 Name: {user.first_name}\n"
        f"🔖 Username: @{user.username if user.username else 'N/A'}\n\n"
        f"💡 Click '🛒 Buy IDs' to purchase"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📞 Support")
def support(m):
    text = (
        f"📞 *Customer Support*\n\n"
        f"👤 Admin: @Rakib0343\n"
        f"💬 Response Time: 5-10 minutes\n\n"
        f"📱 *Payment Numbers:*\n"
        f"├ bKash: `{BKASH_NO}`\n"
        f"└ Nagad: `{NAGAD_NO}`\n\n"
        f"💡 Send money then share TrxID in bot"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📜 My Orders")
def my_orders(m):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, quantity, total_price, trx_id, status, order_time "
        "FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (m.from_user.id,)
    )
    orders = c.fetchall()
    conn.close()

    if not orders:
        bot.send_message(m.chat.id,
                         "📭 *No orders found*\n\nClick '🛒 Buy IDs' to place your first order!",
                         parse_mode="Markdown")
        return

    text = "📜 *Your Order History*\n\n"
    for order in orders:
        emoji = "✅" if order[4] == "Delivered" else "⏳"
        text += (
            f"{emoji} *Order #{order[0]}*\n"
            f"   📦 Quantity: {order[1]}\n"
            f"   💰 Total: {order[2]} TK\n"
            f"   🆔 TrxID: `{order[3]}`\n"
            f"   📊 Status: {order[4]}\n"
            f"   🕒 {order[5]}\n\n"
        )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# ============= BUY FLOW =============

@bot.message_handler(func=lambda m: m.text == "🛒 Buy IDs")
def buy_ids(m):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, price, description FROM products")
    products = c.fetchall()
    conn.close()

    if not products:
        bot.send_message(m.chat.id,
                         "📦 *No products available*\n\nPlease check back later!",
                         parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for product in products:
        conn2 = sqlite3.connect(DB_PATH)
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND sold=0", (product[0],))
        stock = c2.fetchone()[0]
        conn2.close()
        btn_text = f"📦 {product[1]} — {product[2]} TK/ID  (Stock: {stock})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_{product[0]}"))

    bot.send_message(m.chat.id, "📋 *Select a Product:*",
                     reply_markup=markup, parse_mode="Markdown")

# ---- quantity step ----
def process_quantity(message, product_id, price, max_qty):
    try:
        qty = int(message.text.strip())
        if qty < 1:
            bot.send_message(message.chat.id, "❌ Quantity must be at least 1!")
            return
        if qty > max_qty:
            bot.send_message(message.chat.id, f"❌ Only {max_qty} IDs available!")
            return
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid number!")
        return

    total = qty * price
    order_id = f"{message.from_user.id}_{int(time.time())}"

    pending_orders[order_id] = {
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'product_id': product_id,
        'quantity': qty,
        'total_price': total,
        'status': 'pending_payment'
    }

    payment_text = (
        f"💳 *Payment Required*\n\n"
        f"📦 Product ID: {product_id}\n"
        f"🔢 Quantity: {qty}\n"
        f"💰 Total Amount: {total} TK\n\n"
        f"📱 *Send Money to:*\n"
        f"├ bKash: `{BKASH_NO}`\n"
        f"└ Nagad: `{NAGAD_NO}`\n\n"
        f"📝 *Instructions:*\n"
        f"1️⃣ Send exactly {total} TK\n"
        f"2️⃣ After payment, send your *Transaction ID* here\n"
        f"3️⃣ Wait for admin approval\n\n"
        f"✍️ *Enter your Transaction ID:*"
    )
    msg = bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_trx, order_id)

# ---- trx step ----
def process_trx(message, order_id):
    trx_id = message.text.strip().upper()

    if order_id not in pending_orders:
        bot.send_message(message.chat.id, "❌ Order expired! Please start over.")
        return

    order = pending_orders[order_id]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT trx_id FROM used_trx WHERE trx_id=?", (trx_id,))
    if c.fetchone():
        bot.send_message(message.chat.id, "❌ This Transaction ID has already been used!")
        conn.close()
        return
    conn.close()

    order['trx_id'] = trx_id
    order['status'] = 'pending_approval'
    pending_orders[order_id] = order

    bot.send_message(
        message.chat.id,
        f"✅ *Payment information received!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"💰 Amount: {order['total_price']} TK\n"
        f"🆔 TrxID: `{trx_id}`\n\n"
        f"⏳ *Waiting for admin approval...*\n"
        f"Please wait 5-10 minutes.",
        parse_mode="Markdown"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{order_id}"),
        types.InlineKeyboardButton("❌ REJECT",  callback_data=f"reject_{order_id}")
    )
    admin_text = (
        f"🆕 *NEW ORDER PENDING APPROVAL*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"👤 User ID: `{order['user_id']}`\n"
        f"📝 Name: {order['first_name']}\n"
        f"🔖 Username: @{order['username'] if order['username'] else 'N/A'}\n\n"
        f"📦 Product ID: {order['product_id']}\n"
        f"🔢 Quantity: {order['quantity']}\n"
        f"💰 Total Amount: {order['total_price']} TK\n"
        f"🆔 Transaction ID: `{trx_id}`\n\n"
        f"📌 *Select Action:*"
    )
    bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown", reply_markup=markup)

# ============= DELIVERY =============
def deliver_ids(user_id, product_id, quantity, trx_id, total_price):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        c.execute(
            "SELECT id, account_data FROM stock WHERE product_id=? AND sold=0 LIMIT ?",
            (product_id, quantity)
        )
        items = c.fetchall()

        if not items:
            bot.send_message(user_id, "❌ No IDs available! Please contact admin for refund.")
            bot.send_message(ADMIN_ID,
                             f"⚠️ OUT OF STOCK! User {user_id} ordered {quantity} IDs but none available.")
            conn.close()
            return False

        # Build a plain-text file for delivery
        file_lines = []
        file_lines.append(f"FB ID Shop — Your Order")
        file_lines.append(f"Transaction ID : {trx_id}")
        file_lines.append(f"Total Paid     : {total_price} TK")
        file_lines.append(f"Quantity       : {len(items)}")
        file_lines.append("=" * 50)
        file_lines.append("FORMAT: username : password : cookie")
        file_lines.append("=" * 50)

        for idx, item in enumerate(items, 1):
            username, password, cookie = parse_account(item[1])
            file_lines.append(f"\n--- ID #{idx} ---")
            file_lines.append(f"Username : {username}")
            file_lines.append(f"Password : {password}")
            file_lines.append(f"Cookie   : {cookie}")

        file_lines.append("\n" + "=" * 50)
        file_lines.append("⚠️ Change password immediately after login!")
        file_lines.append("📞 Support: @Rakib0343")

        file_content = "\n".join(file_lines).encode('utf-8')

        # Send summary message first
        bot.send_message(
            user_id,
            f"✅ *PAYMENT APPROVED!*\n\n"
            f"📦 Quantity: {len(items)} ID(s)\n"
            f"💰 Total Paid: {total_price} TK\n"
            f"🆔 Transaction ID: `{trx_id}`\n\n"
            f"📎 Your account details are in the file below.\n\n"
            f"⚠️ *IMPORTANT:*\n"
            f"• Change password immediately\n"
            f"• Save cookie for future login\n"
            f"• Use on 1 device initially\n\n"
            f"📞 Support: @Rakib0343",
            parse_mode="Markdown"
        )

        # Send as TXT file
        bot.send_document(
            user_id,
            document=io.BytesIO(file_content),
            visible_file_name=f"order_{trx_id}.txt",
            caption="🔑 Your Facebook Account(s) — Keep this file safe!"
        )

        # Mark sold
        for item in items:
            c.execute("UPDATE stock SET sold=1 WHERE id=?", (item[0],))

        c.execute("INSERT INTO used_trx VALUES (?)", (trx_id,))
        c.execute(
            "INSERT INTO orders (user_id, product_id, quantity, total_price, trx_id, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, product_id, len(items), total_price, trx_id, "Delivered")
        )
        conn.commit()

        c.execute("SELECT name FROM products WHERE id=?", (product_id,))
        row = c.fetchone()
        product_name = row[0] if row else str(product_id)
        conn.close()

        bot.send_message(
            ADMIN_ID,
            f"✅ *SALE COMPLETED!*\n"
            f"👤 User: `{user_id}`\n"
            f"📦 Product: {product_name}\n"
            f"🔢 Quantity: {len(items)} IDs\n"
            f"💰 Amount: {total_price} TK",
            parse_mode="Markdown"
        )
        return True

    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Delivery error: {str(e)}")
        return False

# ============= ALL CALLBACK HANDLER (single handler, no conflicts) =============
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    data = call.data

    # ---- BUY product selected ----
    if data.startswith("buy_"):
        product_id = int(data.split("_", 1)[1])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, price, description FROM products WHERE id=?", (product_id,))
        product = c.fetchone()
        c.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND sold=0", (product_id,))
        available = c.fetchone()[0]
        conn.close()

        if not product:
            bot.answer_callback_query(call.id, "❌ Product not found!", show_alert=True)
            return
        if available == 0:
            bot.answer_callback_query(call.id, "❌ Out of stock!", show_alert=True)
            return

        msg_text = (
            f"🛍 *{product[0]}*\n\n"
            f"💰 Price: {product[1]} TK per ID\n"
            f"📦 Available: {available} IDs\n"
            f"📝 {product[2]}\n\n"
            f"✍️ *How many IDs do you want to buy?*\n"
            f"(Maximum: {available})"
        )
        msg = bot.send_message(call.message.chat.id, msg_text, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_quantity, product_id, product[1], available)
        bot.answer_callback_query(call.id)

    # ---- APPROVE order ----
    elif data.startswith("approve_"):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Admins only!", show_alert=True)
            return
        order_id = data[len("approve_"):]
        if order_id not in pending_orders:
            bot.answer_callback_query(call.id, "❌ Order not found or already processed!", show_alert=True)
            return
        order = pending_orders[order_id]
        bot.answer_callback_query(call.id, "⏳ Processing...")
        try:
            bot.edit_message_text(f"⏳ Approving Order `{order_id}`...",
                                  call.message.chat.id, call.message.message_id,
                                  parse_mode="Markdown")
        except Exception:
            pass
        success = deliver_ids(order['user_id'], order['product_id'], order['quantity'],
                              order['trx_id'], order['total_price'])
        if success:
            try:
                bot.edit_message_text(f"✅ *ORDER {order_id} APPROVED!* IDs delivered via file.",
                                      call.message.chat.id, call.message.message_id,
                                      parse_mode="Markdown")
            except Exception:
                pass
            del pending_orders[order_id]
        else:
            try:
                bot.edit_message_text(f"❌ *FAILED!* Order {order_id} — Out of stock.",
                                      call.message.chat.id, call.message.message_id,
                                      parse_mode="Markdown")
            except Exception:
                pass

    # ---- REJECT order ----
    elif data.startswith("reject_"):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Admins only!", show_alert=True)
            return
        order_id = data[len("reject_"):]
        if order_id not in pending_orders:
            bot.answer_callback_query(call.id, "❌ Order not found!", show_alert=True)
            return
        order = pending_orders[order_id]
        bot.answer_callback_query(call.id, "❌ Rejecting...")
        bot.send_message(
            order['user_id'],
            f"❌ *PAYMENT REJECTED*\n\n"
            f"Your payment could not be verified.\n"
            f"🆔 Order ID: `{order_id}`\n"
            f"💰 Amount: {order['total_price']} TK\n\n"
            f"📞 Contact support: @Rakib0343",
            parse_mode="Markdown"
        )
        try:
            bot.edit_message_text(f"❌ *ORDER {order_id} REJECTED!*",
                                  call.message.chat.id, call.message.message_id,
                                  parse_mode="Markdown")
        except Exception:
            pass
        del pending_orders[order_id]

    # ---- ADMIN: open panel ----
    elif data == "admin_add_product":
        if call.from_user.id != ADMIN_ID:
            return
        msg = bot.send_message(call.message.chat.id, "✍️ *Enter Product Name:*", parse_mode="Markdown")
        bot.register_next_step_handler(msg, get_product_name)
        bot.answer_callback_query(call.id)

    elif data == "admin_del_product":
        if call.from_user.id != ADMIN_ID:
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name FROM products")
        products = c.fetchall()
        conn.close()
        if not products:
            bot.answer_callback_query(call.id, "No products to delete!", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for p in products:
            markup.add(types.InlineKeyboardButton(f"❌ {p[1]}", callback_data=f"del_{p[0]}"))
        try:
            bot.edit_message_text("🗑️ *Select product to delete:*",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif data.startswith("del_"):
        if call.from_user.id != ADMIN_ID:
            return
        pid = data.split("_", 1)[1]
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (pid,))
        c.execute("DELETE FROM stock WHERE product_id=?", (pid,))
        conn.commit()
        conn.close()
        try:
            bot.edit_message_text("✅ *Product deleted!*",
                                  call.message.chat.id, call.message.message_id,
                                  parse_mode="Markdown")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif data == "admin_add_stock":
        if call.from_user.id != ADMIN_ID:
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, name FROM products")
        products = c.fetchall()
        conn.close()
        if not products:
            bot.answer_callback_query(call.id, "No products! Add a product first.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for p in products:
            markup.add(types.InlineKeyboardButton(f"📦 {p[1]}", callback_data=f"stock_{p[0]}"))
        try:
            bot.edit_message_text("📁 *Select product to add IDs:*",
                                  call.message.chat.id, call.message.message_id,
                                  reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif data.startswith("stock_"):
        if call.from_user.id != ADMIN_ID:
            return
        product_id = data.split("_", 1)[1]
        pending_orders[f"upload_{call.from_user.id}"] = product_id
        try:
            bot.edit_message_text(
                f"📤 *Send TXT file for Product ID {product_id}*\n\n"
                f"*Format (one per line):*\n"
                f"`username:password:cookie`\n\n"
                f"*Example:*\n"
                f"`john\\_doe:pass123:EAABsbCxxx...`\n\n"
                f"📎 Send the .txt file as a document.",
                call.message.chat.id, call.message.message_id,
                parse_mode="Markdown"
            )
        except Exception:
            pass
        bot.answer_callback_query(call.id)

    elif data == "admin_pending":
        if call.from_user.id != ADMIN_ID:
            return
        pending = {k: v for k, v in pending_orders.items()
                   if v.get('status') == 'pending_approval'}
        if not pending:
            bot.send_message(call.message.chat.id, "📭 No pending orders!")
            bot.answer_callback_query(call.id)
            return
        for order_id, order in pending.items():
            text = (
                f"⏳ *PENDING ORDER*\n\n"
                f"🆔 Order ID: `{order_id}`\n"
                f"👤 User: `{order['user_id']}`\n"
                f"📝 Name: {order.get('first_name', 'N/A')}\n"
                f"🔢 Quantity: {order['quantity']}\n"
                f"💰 Total: {order['total_price']} TK\n"
                f"🆔 TrxID: `{order['trx_id']}`"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{order_id}"),
                types.InlineKeyboardButton("❌ Reject",  callback_data=f"reject_{order_id}")
            )
            bot.send_message(call.message.chat.id, text,
                             parse_mode="Markdown", reply_markup=markup)
        bot.answer_callback_query(call.id)

    else:
        bot.answer_callback_query(call.id)

# ============= ADMIN PANEL (keyboard buttons) =============

@bot.message_handler(func=lambda m: m.text == "🛠 Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel(m):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Product",    callback_data="admin_add_product"),
        types.InlineKeyboardButton("❌ Delete Product", callback_data="admin_del_product"),
        types.InlineKeyboardButton("📦 Add Stock (TXT)", callback_data="admin_add_stock"),
        types.InlineKeyboardButton("⏳ Pending Orders", callback_data="admin_pending")
    )
    bot.send_message(m.chat.id, "🔐 *ADMIN CONTROL PANEL*",
                     reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 Statistics" and m.from_user.id == ADMIN_ID)
def admin_stats(m):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM products")
    products = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM stock WHERE sold=0")
    available = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM stock WHERE sold=1")
    sold = c.fetchone()[0]
    c.execute("SELECT SUM(total_price) FROM orders WHERE status='Delivered'")
    earnings = c.fetchone()[0] or 0
    conn.close()
    pending = len([o for o in pending_orders.values() if o.get('status') == 'pending_approval'])
    text = (
        f"📊 *BOT STATISTICS*\n\n"
        f"📦 Products: {products}\n"
        f"🔑 Available IDs: {available}\n"
        f"✅ Sold IDs: {sold}\n"
        f"💰 Earnings: {earnings} TK\n"
        f"⏳ Pending Orders: {pending}"
    )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📦 Stock Status" and m.from_user.id == ADMIN_ID)
def admin_stock(m):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT p.name,
               COUNT(s.id),
               SUM(CASE WHEN s.sold=0 THEN 1 ELSE 0 END),
               SUM(CASE WHEN s.sold=1 THEN 1 ELSE 0 END)
        FROM products p
        LEFT JOIN stock s ON p.id = s.product_id
        GROUP BY p.id
    """)
    data = c.fetchall()
    conn.close()
    if not data:
        bot.send_message(m.chat.id, "📦 No stock found!")
        return
    text = "📋 *STOCK STATUS*\n\n"
    for name, total, available, sold in data:
        text += (
            f"📦 *{name}*\n"
            f"   ├ Total: {total or 0}\n"
            f"   ├ Available: {available or 0}\n"
            f"   └ Sold: {sold or 0}\n\n"
        )
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

# ============= ADD PRODUCT steps =============

def get_product_name(message):
    if message.from_user.id != ADMIN_ID:
        return
    name = message.text.strip()
    msg = bot.send_message(message.chat.id, "💰 *Enter Price per ID (number only):*",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_product_price, name)

def get_product_price(message, name):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        price = float(message.text.strip())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid price! Please enter a number.")
        return
    msg = bot.send_message(message.chat.id, "📝 *Enter Product Description:*",
                           parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_product_desc, name, price)

def get_product_desc(message, name, price):
    if message.from_user.id != ADMIN_ID:
        return
    desc = message.text.strip()[:200]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, description) VALUES (?, ?, ?)", (name, price, desc))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id,
                     f"✅ *Product Added!*\n\n📦 {name}\n💰 {price} TK per ID",
                     parse_mode="Markdown")

# ============= TXT FILE UPLOAD =============

@bot.message_handler(content_types=['document'])
def handle_txt_upload(message):
    if message.from_user.id != ADMIN_ID:
        return
    key = f"upload_{message.from_user.id}"
    if key not in pending_orders:
        bot.send_message(message.chat.id,
                         "⚠️ Please select a product first via Admin Panel → Add Stock.")
        return
    product_id = pending_orders[key]
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        content = downloaded.decode('utf-8', errors='ignore')
        lines = content.splitlines()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        count = 0
        skipped = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Accept any non-empty line; warn if format looks wrong
            if ':' not in line:
                skipped += 1
                continue
            c.execute("INSERT INTO stock (product_id, account_data, sold) VALUES (?, ?, 0)",
                      (int(product_id), line))
            count += 1
        conn.commit()
        conn.close()

        msg = f"✅ *Stock Updated!*\n\n📦 Added: {count} IDs"
        if skipped:
            msg += f"\n⚠️ Skipped (no colon): {skipped} lines"
        msg += f"\n\n*Expected format per line:*\n`username:password:cookie`"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        del pending_orders[key]

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error reading file: {str(e)}")

# ============= RUN =============
if __name__ == "__main__":
    print("=" * 50)
    print("🚀 FB ID SELL BOT — READY FOR UBUNTU")
    print("=" * 50)
    print(f"Token : {TOKEN[:15]}...")
    print(f"Admin : {ADMIN_ID}")
    print(f"Database: {DB_PATH}")
    print("Stock format : username:password:cookie")
    print("=" * 50)
    
    # Start bot with error handling
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except KeyboardInterrupt:
            print("\n👋 Bot stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)
