import telebot
import random
import time
import sqlite3
import threading
import os
import logging
from datetime import datetime
from flask import Flask

# === SECURITY CONFIGURATION ===
# Set up logging for security monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)

# === BOT CONFIG ===
BOT_TOKEN = "8032628262:AAGM4SHGrH_XTNjVFtgUO18QUtQqiH0TIxo"
ADMIN_ID = 6011041717

# Security: Input validation
def validate_user_input(input_str, max_length=100):
    if not input_str or len(input_str) > max_length:
        return False
    # Basic sanitization
    dangerous_chars = [';', '--', '/*', '*/', 'xp_', 'union', 'select', 'drop', 'delete', 'insert', 'update']
    input_lower = input_str.lower()
    return not any(char in input_lower for char in dangerous_chars)

bot = telebot.TeleBot(BOT_TOKEN)

# === PORT CONFIGURATION FOR RENDER ===
app = Flask(__name__)
port = int(os.environ.get('PORT', 5000))

@app.route('/')
def home():
    return "🎮 Mines Bot is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=port)

# Start Flask in a separate thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# === ENHANCED MINES GAME ENGINE ===
class MinesGame:
    def __init__(self):
        self.grid_size = 5
        self.total_tiles = 25
        self.mines_count = 3
        self.multipliers = {
            1: 1.10, 2: 1.21, 3: 1.33, 4: 1.46, 5: 1.61
        }
    
    def generate_grid(self):
        all_positions = list(range(self.total_tiles))
        mines = random.sample(all_positions, self.mines_count)
        return mines
    
    def calculate_multiplier(self, tiles_opened):
        multiplier = self.multipliers.get(tiles_opened, 1.0)
        return min(multiplier, 5.0)
    
    def get_grid_display(self, opened_tiles, mines, game_over=False):
        grid = ""
        for i in range(self.total_tiles):
            if i in opened_tiles:
                if i in mines:
                    grid += "💥"
                else:
                    grid += "🟢"
            elif game_over and i in mines:
                grid += "💣"
            else:
                grid += "⬜"
            
            if (i + 1) % self.grid_size == 0:
                grid += "\n"
        return grid

# === SECURE PAYMENT SYSTEM ===
class PaymentSystem:
    def __init__(self):
        self.setup_database()
        
    def get_connection(self):
        """Create a new database connection for each thread with security"""
        try:
            conn = sqlite3.connect('mines.db', check_same_thread=False, timeout=10)
            # Enable foreign keys for data integrity
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        except sqlite3.Error as e:
            logging.error(f"Database connection error: {e}")
            raise
        
    def setup_database(self):
        conn = self.get_connection()
        c = conn.cursor()
        
        # Create tables with proper constraints
        c.execute('''CREATE TABLE IF NOT EXISTS user_balances
                     (user_id INTEGER PRIMARY KEY, 
                      balance REAL DEFAULT 0.0 CHECK(balance >= 0),
                      created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS deposit_requests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      amount REAL NOT NULL CHECK(amount > 0),
                      receipt_file_id TEXT,
                      status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (user_id) REFERENCES user_balances(user_id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER NOT NULL,
                      amount REAL NOT NULL CHECK(amount > 0),
                      status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (user_id) REFERENCES user_balances(user_id))''')
        
        # Create indexes for better performance
        c.execute('''CREATE INDEX IF NOT EXISTS idx_deposit_status ON deposit_requests(status)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON withdrawal_requests(status)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_deposit_user ON deposit_requests(user_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_withdrawal_user ON withdrawal_requests(user_id)''')
        
        conn.commit()
        conn.close()
    
    def get_user_balance(self, user_id):
        """Secure balance retrieval with transaction"""
        if not validate_user_input(str(user_id)):
            logging.warning(f"Invalid user_id format: {user_id}")
            return 0.0
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute("SELECT balance FROM user_balances WHERE user_id=?", (user_id,))
            result = c.fetchone()
            
            if result:
                balance = result[0]
            else:
                # If user doesn't exist, insert with 0 balance
                c.execute("INSERT INTO user_balances (user_id, balance) VALUES (?, ?)", (user_id, 0.0))
                conn.commit()
                balance = 0.0
                logging.info(f"Created new user account: {user_id}")
            
            return float(balance)
            
        except sqlite3.Error as e:
            logging.error(f"Error getting balance for user {user_id}: {e}")
            return 0.0
        finally:
            conn.close()
    
    def update_balance(self, user_id, amount):
        """Secure balance update with transaction"""
        if not validate_user_input(str(user_id)) or not isinstance(amount, (int, float)):
            logging.warning(f"Invalid input for update_balance: user_id={user_id}, amount={amount}")
            return 0.0
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            # First ensure user exists
            self.get_user_balance(user_id)
            
            # Update balance with transaction
            c.execute("UPDATE user_balances SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            
            if c.rowcount == 0:
                logging.error(f"Failed to update balance for user {user_id}")
                conn.rollback()
                return 0.0
                
            conn.commit()
            
            # Get new balance
            c.execute("SELECT balance FROM user_balances WHERE user_id=?", (user_id,))
            result = c.fetchone()
            new_balance = float(result[0]) if result else 0.0
            
            logging.info(f"Balance updated: user {user_id}, change: {amount}, new balance: {new_balance}")
            return new_balance
            
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error updating balance for user {user_id}: {e}")
            return 0.0
        finally:
            conn.close()
    
    def get_all_balances(self):
        """Secure retrieval of all balances"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute("SELECT user_id, balance FROM user_balances")
            results = c.fetchall()
            return results
        except sqlite3.Error as e:
            logging.error(f"Error getting all balances: {e}")
            return []
        finally:
            conn.close()
    
    def set_balance(self, user_id, amount):
        """Secure balance setting"""
        if not validate_user_input(str(user_id)) or not isinstance(amount, (int, float)) or amount < 0:
            logging.warning(f"Invalid input for set_balance: user_id={user_id}, amount={amount}")
            return False
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute("INSERT OR REPLACE INTO user_balances (user_id, balance) VALUES (?, ?)", (user_id, amount))
            conn.commit()
            logging.info(f"Balance set: user {user_id}, amount: {amount}")
            return True
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error setting balance for user {user_id}: {e}")
            return False
        finally:
            conn.close()
    
    def create_deposit_request(self, user_id, amount, receipt_file_id=None):
        """Secure deposit request creation"""
        if not validate_user_input(str(user_id)) or not isinstance(amount, (int, float)) or amount <= 0:
            logging.warning(f"Invalid deposit request: user_id={user_id}, amount={amount}")
            return None
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO deposit_requests 
                         (user_id, amount, receipt_file_id, status, timestamp) 
                         VALUES (?, ?, ?, ?, ?)''',
                      (user_id, amount, receipt_file_id, 'pending', datetime.now()))
            request_id = c.lastrowid
            conn.commit()
            logging.info(f"Deposit request created: #{request_id} for user {user_id}, amount: {amount}")
            return request_id
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error creating deposit request: {e}")
            return None
        finally:
            conn.close()
    
    def create_withdrawal_request(self, user_id, amount):
        """Secure withdrawal request creation"""
        if not validate_user_input(str(user_id)) or not isinstance(amount, (int, float)) or amount <= 0:
            logging.warning(f"Invalid withdrawal request: user_id={user_id}, amount={amount}")
            return None
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO withdrawal_requests 
                         (user_id, amount, status, timestamp) 
                         VALUES (?, ?, ?, ?)''',
                      (user_id, amount, 'pending', datetime.now()))
            request_id = c.lastrowid
            conn.commit()
            logging.info(f"Withdrawal request created: #{request_id} for user {user_id}, amount: {amount}")
            return request_id
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error creating withdrawal request: {e}")
            return None
        finally:
            conn.close()
    
    def get_pending_deposits(self):
        """Secure retrieval of pending deposits"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('''SELECT d.*, u.balance 
                         FROM deposit_requests d 
                         LEFT JOIN user_balances u ON d.user_id = u.user_id 
                         WHERE d.status = 'pending' 
                         ORDER BY d.timestamp''')
            results = c.fetchall()
            return results
        except sqlite3.Error as e:
            logging.error(f"Error getting pending deposits: {e}")
            return []
        finally:
            conn.close()
    
    def get_pending_withdrawals(self):
        """Secure retrieval of pending withdrawals"""
        conn = self.get_connection()
        c = conn.cursor()
        try:
            c.execute('''SELECT w.*, u.balance 
                         FROM withdrawal_requests w 
                         LEFT JOIN user_balances u ON w.user_id = u.user_id 
                         WHERE w.status = 'pending' 
                         ORDER BY w.timestamp''')
            results = c.fetchall()
            return results
        except sqlite3.Error as e:
            logging.error(f"Error getting pending withdrawals: {e}")
            return []
        finally:
            conn.close()
    
    def update_deposit_status(self, request_id, status, admin_id=ADMIN_ID):
        """Secure deposit status update with transaction"""
        if not validate_user_input(str(request_id)) or status not in ['approved', 'rejected']:
            logging.warning(f"Invalid deposit status update: request_id={request_id}, status={status}")
            return False
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            # Get deposit info first
            c.execute('''SELECT user_id, amount FROM deposit_requests 
                         WHERE id = ? AND status = 'pending' ''', (request_id,))
            deposit = c.fetchone()
            
            if not deposit:
                logging.warning(f"Deposit request #{request_id} not found or not pending")
                return False
                
            user_id, amount = deposit
            
            if status == 'approved':
                # Add funds to user balance
                c.execute("UPDATE user_balances SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                if c.rowcount == 0:
                    conn.rollback()
                    return False
            
            # Update deposit status
            c.execute("UPDATE deposit_requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()
            
            logging.info(f"Deposit #{request_id} {status} by admin {admin_id} for user {user_id}")
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error updating deposit status for request #{request_id}: {e}")
            return False
        finally:
            conn.close()
    
    def update_withdrawal_status(self, request_id, status, admin_id=ADMIN_ID):
        """Secure withdrawal status update with transaction"""
        if not validate_user_input(str(request_id)) or status not in ['approved', 'rejected']:
            logging.warning(f"Invalid withdrawal status update: request_id={request_id}, status={status}")
            return False
            
        conn = self.get_connection()
        c = conn.cursor()
        
        try:
            # Get withdrawal info first
            c.execute('''SELECT user_id, amount FROM withdrawal_requests 
                         WHERE id = ? AND status = 'pending' ''', (request_id,))
            withdrawal = c.fetchone()
            
            if not withdrawal:
                logging.warning(f"Withdrawal request #{request_id} not found or not pending")
                return False
                
            user_id, amount = withdrawal
            
            if status == 'rejected':
                # Refund the amount
                c.execute("UPDATE user_balances SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
                if c.rowcount == 0:
                    conn.rollback()
                    return False
            
            # Update withdrawal status
            c.execute("UPDATE withdrawal_requests SET status = ? WHERE id = ?", (status, request_id))
            conn.commit()
            
            logging.info(f"Withdrawal #{request_id} {status} by admin {admin_id} for user {user_id}")
            return True
            
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Error updating withdrawal status for request #{request_id}: {e}")
            return False
        finally:
            conn.close()

# === GLOBAL VARIABLES ===
mines_game = MinesGame()
payment_system = PaymentSystem()

active_games = {}
MIN_STAKE = 30
MIN_WITHDRAWAL = 100

def is_authorized_admin(user_id):
    """Check if user is authorized admin"""
    return user_id == ADMIN_ID

# === BUTTON CREATION ===
def create_main_menu():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🎮 Play Game", callback_data="play_game"),
        InlineKeyboardButton("💰 Deposit", callback_data="deposit_menu")
    )
    markup.row(
        InlineKeyboardButton("💳 Withdraw", callback_data="withdraw_menu"),
        InlineKeyboardButton("📊 Statistics", callback_data="show_stats")
    )
    markup.row(
        InlineKeyboardButton("ℹ️ Help", callback_data="show_help")
    )
    return markup

def create_deposit_menu():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("₦100", callback_data="deposit_100"),
        InlineKeyboardButton("₦200", callback_data="deposit_200"),
        InlineKeyboardButton("₦500", callback_data="deposit_500")
    )
    markup.row(
        InlineKeyboardButton("₦1,000", callback_data="deposit_1000"),
        InlineKeyboardButton("₦2,000", callback_data="deposit_2000"),
        InlineKeyboardButton("₦5,000", callback_data="deposit_5000")
    )
    markup.row(
        InlineKeyboardButton("₦10,000", callback_data="deposit_10000"),
        InlineKeyboardButton("₦20,000", callback_data="deposit_20000")
    )
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return markup

def create_withdraw_menu():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("₦100", callback_data="withdraw_100"),
        InlineKeyboardButton("₦200", callback_data="withdraw_200"),
        InlineKeyboardButton("₦500", callback_data="withdraw_500")
    )
    markup.row(
        InlineKeyboardButton("₦1,000", callback_data="withdraw_1000"),
        InlineKeyboardButton("₦2,000", callback_data="withdraw_2000"),
        InlineKeyboardButton("₦5,000", callback_data="withdraw_5000")
    )
    markup.row(
        InlineKeyboardButton("₦10,000", callback_data="withdraw_10000"),
        InlineKeyboardButton("₦20,000", callback_data="withdraw_20000")
    )
    markup.row(InlineKeyboardButton("🔙 Back", callback_data="main_menu"))
    return markup

def create_number_keyboard(opened_tiles):
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    row = []
    
    for i in range(1, 26):
        if i-1 in opened_tiles:
            row.append(InlineKeyboardButton("✅", callback_data=f"opened_{i}"))
        else:
            row.append(InlineKeyboardButton(str(i), callback_data=f"open_{i}"))
        
        if i % 5 == 0:
            markup.row(*row)
            row = []
    
    markup.row(
        InlineKeyboardButton("💰 Cashout", callback_data="cashout"),
        InlineKeyboardButton("🔮 Predict", callback_data="predict")
    )
    markup.row(InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))
    return markup

def create_admin_panel():
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton("👥 Users", callback_data="admin_users")
    )
    markup.row(
        InlineKeyboardButton("💰 Add Balance", callback_data="admin_add"),
        InlineKeyboardButton("💳 Deposits", callback_data="admin_deposits")
    )
    markup.row(
        InlineKeyboardButton("💸 Withdrawals", callback_data="admin_withdrawals"),
        InlineKeyboardButton("📨 Message User", callback_data="admin_message")
    )
    markup.row(
        InlineKeyboardButton("🔧 Settings", callback_data="admin_settings")
    )
    return markup

# === USER HANDLERS ===
@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Input validation
        if not validate_user_input(user_name):
            user_name = "User"
            
        balance = payment_system.get_user_balance(user_id)
        
        welcome_msg = f"""
🎮 **MINES MASTER** 🎮

👋 Welcome, {user_name}!

💼 Balance: ₦{balance:,.2f}
🎯 Min Bet: ₦{MIN_STAKE:,.2f}
💸 Min Withdrawal: ₦{MIN_WITHDRAWAL:,.2f}
🚀 Max Win: 5X Multiplier

Choose an option:"""
        
        bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_menu())
    except Exception as e:
        logging.error(f"Error in start: {e}")
        bot.send_message(message.chat.id, "🚨 Bot is starting up, please try again in a moment...")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_clicks(call):
    try:
        user_id = call.from_user.id
        data = call.data
            
        if data == "main_menu":
            show_main_menu(call)
        elif data == "play_game":
            start_game(call)
        elif data == "deposit_menu":
            show_deposit_menu(call)
        elif data == "withdraw_menu":
            show_withdraw_menu(call)
        elif data == "show_stats":
            show_stats(call)
        elif data == "show_help":
            show_help(call)
        elif data == "cashout":
            cashout_game(call)
        elif data == "predict":
            show_prediction(call)
        elif data.startswith("deposit_"):
            process_deposit_amount(call, data)
        elif data.startswith("withdraw_"):
            process_withdraw_amount(call, data)
        elif data.startswith("open_"):
            handle_tile_click(call, data)
        elif data.startswith("admin_"):
            handle_admin_clicks(call)
        elif data.startswith("approve_deposit_") or data.startswith("reject_deposit_"):
            handle_admin_clicks(call)
        elif data.startswith("approve_withdrawal_") or data.startswith("reject_withdrawal_"):
            handle_admin_clicks(call)
    except Exception as e:
        logging.error(f"Error in callback: {e}")
        bot.answer_callback_query(call.id, "❌ Error occurred, please try again")

def show_main_menu(call):
    try:
        user_id = call.from_user.id
        user_name = call.from_user.first_name
        balance = payment_system.get_user_balance(user_id)
        
        menu_msg = f"""
🏠 Main Menu

👤 {user_name}
💼 Balance: ₦{balance:,.2f}
🚀 Max Win: 5X

Choose an option:"""
        
        bot.edit_message_text(menu_msg, call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())
    except Exception as e:
        logging.error(f"Error in show_main_menu: {e}")

def show_deposit_menu(call):
    try:
        user_id = call.from_user.id
        balance = payment_system.get_user_balance(user_id)
        
        deposit_msg = f"""
💳 Deposit Funds

💼 Balance: ₦{balance:,.2f}

Select amount:"""
        
        bot.edit_message_text(deposit_msg, call.message.chat.id, call.message.message_id, reply_markup=create_deposit_menu())
    except Exception as e:
        logging.error(f"Error in show_deposit_menu: {e}")

def show_withdraw_menu(call):
    try:
        user_id = call.from_user.id
        balance = payment_system.get_user_balance(user_id)
        
        withdraw_msg = f"""
💸 Withdraw Funds

💼 Balance: ₦{balance:,.2f}
💰 Min Withdrawal: ₦{MIN_WITHDRAWAL:,}

Select amount:"""
        
        bot.edit_message_text(withdraw_msg, call.message.chat.id, call.message.message_id, reply_markup=create_withdraw_menu())
    except Exception as e:
        logging.error(f"Error in show_withdraw_menu: {e}")

def process_deposit_amount(call, data):
    try:
        user_id = call.from_user.id
        amount = int(data.split("_")[1])
        
        deposit_msg = f"""
💳 Deposit Request

💰 Amount: ₦{amount:,}
📸 Please send your payment receipt as a photo.

⚠️ Your deposit will be processed after verification."""
        
        bot.edit_message_text(deposit_msg, call.message.chat.id, call.message.message_id)
        
        # Store the deposit amount in user data for receipt handling
        bot.register_next_step_handler(call.message, process_deposit_receipt, amount)
        
    except Exception as e:
        logging.error(f"Error in process_deposit_amount: {e}")

def process_deposit_receipt(message, amount):
    try:
        user_id = message.from_user.id
        
        if message.photo:
            # Get the largest photo file_id
            file_id = message.photo[-1].file_id
            receipt_file_id = file_id
            
            # Create deposit request
            request_id = payment_system.create_deposit_request(user_id, amount, receipt_file_id)
            
            if request_id:
                # Notify user
                user_msg = f"""
✅ Deposit Request Submitted

💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}
⏳ Status: Pending Verification

Your deposit will be processed within 10-30 minutes after verification."""
                
                bot.send_message(user_id, user_msg, reply_markup=create_main_menu())
                
                # Notify admin
                admin_msg = f"""
🆕 New Deposit Request

👤 User: {user_id} ({message.from_user.first_name})
💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}

Use /admin to manage requests."""
                
                bot.send_message(ADMIN_ID, admin_msg)
                
                # Send receipt to admin
                bot.send_photo(ADMIN_ID, receipt_file_id, caption=f"Receipt for Request #{request_id}")
            else:
                bot.send_message(user_id, "❌ Error creating deposit request. Please try again.")
            
        else:
            bot.send_message(user_id, "❌ Please send a photo of your payment receipt. Use /start to try again.")
            
    except Exception as e:
        logging.error(f"Error in process_deposit_receipt: {e}")
        bot.send_message(user_id, "❌ Error processing receipt. Use /start to try again.")

def process_withdraw_amount(call, data):
    try:
        user_id = call.from_user.id
        amount = int(data.split("_")[1])
        balance = payment_system.get_user_balance(user_id)
        
        if amount < MIN_WITHDRAWAL:
            bot.answer_callback_query(call.id, f"❌ Min withdrawal is ₦{MIN_WITHDRAWAL:,}")
            return
            
        if balance < amount:
            bot.answer_callback_query(call.id, "❌ Insufficient balance")
            return
        
        # Create withdrawal request
        request_id = payment_system.create_withdrawal_request(user_id, amount)
        
        if request_id:
            # Deduct amount from balance temporarily
            new_balance = payment_system.update_balance(user_id, -amount)
            
            withdraw_msg = f"""
✅ Withdrawal Request Submitted

💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}
⏳ Status: Pending Approval
💼 New Balance: ₦{new_balance:,}

Your withdrawal will be processed within 10-30 minutes."""
            
            bot.edit_message_text(withdraw_msg, call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())
            
            # Notify admin
            admin_msg = f"""
🆕 New Withdrawal Request

👤 User: {user_id} ({call.from_user.first_name})
💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}
💼 User Balance: ₦{new_balance:,}

Use /admin to manage requests."""
            
            bot.send_message(ADMIN_ID, admin_msg)
        else:
            bot.answer_callback_query(call.id, "❌ Error creating withdrawal request")
        
    except Exception as e:
        logging.error(f"Error in process_withdraw_amount: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing withdrawal")

def start_game(call):
    try:
        user_id = call.from_user.id
        balance = payment_system.get_user_balance(user_id)
        
        if user_id in active_games:
            bot.answer_callback_query(call.id, "⚠️ Active game!")
            return
        
        if balance < MIN_STAKE:
            bot.edit_message_text(
                f"❌ Insufficient Balance\n💼 Current: ₦{balance:,}\n🎯 Required: ₦{MIN_STAKE:,}",
                call.message.chat.id, call.message.message_id, reply_markup=create_deposit_menu()
            )
            return
        
        bet_amount = MIN_STAKE
        new_balance = payment_system.update_balance(user_id, -bet_amount)
        
        mines = mines_game.generate_grid()
        # Randomly decide which click will have the forced bomb (1st, 2nd, or 3rd)
        forced_bomb_click = random.randint(1, 3)
        
        active_games[user_id] = {
            'mines': mines,
            'opened_tiles': [],
            'bet_amount': bet_amount,
            'click_count': 0,
            'forced_bomb_click': forced_bomb_click,  # Random click (1, 2, or 3) that will trigger bomb
            'forced_bomb_tile': None
        }
        
        grid = mines_game.get_grid_display([], mines)
        game_msg = f"""
🎮 MINES GAME

{grid}
💣 Mines: 3
💰 Bet: ₦{bet_amount:,}
🎯 Multiplier: 1.00x
💼 Balance: ₦{new_balance:,}

Tap a number:"""
        
        bot.edit_message_text(game_msg, call.message.chat.id, call.message.message_id, reply_markup=create_number_keyboard([]))
    except Exception as e:
        logging.error(f"Error in start_game: {e}")
        bot.answer_callback_query(call.id, "❌ Error starting game")

def handle_tile_click(call, data):
    try:
        user_id = call.from_user.id
        if user_id not in active_games:
            bot.answer_callback_query(call.id, "❌ No game!")
            return
        
        tile_number = int(data.split("_")[1]) - 1
        
        if tile_number in active_games[user_id]['opened_tiles']:
            bot.answer_callback_query(call.id, "✅ Already opened!")
            return
        
        active_games[user_id]['click_count'] += 1
        
        # RANDOM FORCE BOMB FEATURE - Random click (1st, 2nd, or 3rd) will trigger bomb
        if active_games[user_id]['click_count'] == active_games[user_id]['forced_bomb_click']:
            if active_games[user_id]['forced_bomb_tile'] is None:
                active_games[user_id]['forced_bomb_tile'] = tile_number
                if tile_number not in active_games[user_id]['mines']:
                    # Remove a random mine and add it to the current tile
                    if active_games[user_id]['mines']:
                        active_games[user_id]['mines'].remove(random.choice(active_games[user_id]['mines']))
                    active_games[user_id]['mines'].append(tile_number)
        
        active_games[user_id]['opened_tiles'].append(tile_number)
        
        if tile_number in active_games[user_id]['mines']:
            grid = mines_game.get_grid_display(active_games[user_id]['opened_tiles'], active_games[user_id]['mines'], True)
            loss_msg = f"""
💥 GAME OVER

{grid}
🎯 Reached: {mines_game.calculate_multiplier(len(active_games[user_id]['opened_tiles'])-1):.2f}x
💸 Lost: ₦{active_games[user_id]['bet_amount']:,}
💼 Balance: ₦{payment_system.get_user_balance(user_id):,}"""
            
            del active_games[user_id]
            bot.edit_message_text(loss_msg, call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())
        else:
            tiles = len(active_games[user_id]['opened_tiles'])
            multiplier = mines_game.calculate_multiplier(tiles)
            potential = active_games[user_id]['bet_amount'] * multiplier
            
            grid = mines_game.get_grid_display(active_games[user_id]['opened_tiles'], active_games[user_id]['mines'])
            continue_msg = f"""
🎮 MINES GAME

{grid}
✅ Tiles: {tiles}
🎯 Multiplier: {multiplier:.2f}x
💰 Potential: ₦{potential:,}
🔄 Click: {active_games[user_id]['click_count']}/3"""
            
            bot.edit_message_text(continue_msg, call.message.chat.id, call.message.message_id, 
                                reply_markup=create_number_keyboard(active_games[user_id]['opened_tiles']))
            bot.answer_callback_query(call.id, f"✅ Safe! {multiplier:.2f}x")
    except Exception as e:
        logging.error(f"Error in handle_tile_click: {e}")
        bot.answer_callback_query(call.id, "❌ Error processing move")

def cashout_game(call):
    try:
        user_id = call.from_user.id
        if user_id not in active_games:
            bot.answer_callback_query(call.id, "❌ No game!")
            return
        
        game = active_games[user_id]
        tiles = len(game['opened_tiles'])
        multiplier = mines_game.calculate_multiplier(tiles)
        winnings = game['bet_amount'] * multiplier
        
        new_balance = payment_system.update_balance(user_id, winnings)
        grid = mines_game.get_grid_display(game['opened_tiles'], game['mines'], True)
        
        result_msg = f"""
💰 CASHOUT SUCCESSFUL

{grid}
📈 Tiles: {tiles}
🎯 Multiplier: {multiplier:.2f}x
💵 Bet: ₦{game['bet_amount']:,}
🎊 Won: ₦{winnings:,}
💼 Balance: ₦{new_balance:,}"""
        
        del active_games[user_id]
        bot.edit_message_text(result_msg, call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())
    except Exception as e:
        logging.error(f"Error in cashout_game: {e}")
        bot.answer_callback_query(call.id, "❌ Error cashing out")

def show_prediction(call):
    bot.answer_callback_query(call.id, "🔮 Prediction: Try random tiles!", show_alert=True)

def show_stats(call):
    try:
        user_id = call.from_user.id
        balance = payment_system.get_user_balance(user_id)
        bot.edit_message_text(f"📊 Statistics\n💼 Balance: ₦{balance:,}", 
                             call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())
    except Exception as e:
        logging.error(f"Error in show_stats: {e}")

def show_help(call):
    help_msg = """
ℹ️ How to Play

🎮 Game Rules:
• 5x5 grid, 3 mines
• Open tiles, avoid mines
• Cash out anytime
• Max 5X multiplier
• Random force bomb feature

💳 Deposits:
• Select amount
• Send receipt photo
• Wait for verification

💸 Withdrawals:
• Min ₦100 withdrawal
• Request processing
• Balance deducted temporarily

🎯 Tips:
• Cash out early
• Start small"""
    
    bot.edit_message_text(help_msg, call.message.chat.id, call.message.message_id, reply_markup=create_main_menu())

# === ADMIN COMMANDS ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_authorized_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied")
        logging.warning(f"Unauthorized admin access attempt: {message.from_user.id}")
        return
    
    bot.send_message(message.chat.id, "🔧 Admin Panel", reply_markup=create_admin_panel())

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if not is_authorized_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "Usage: /addbalance USER_ID AMOUNT")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        new_balance = payment_system.update_balance(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Added ₦{amount:,} to user {user_id}\nNew balance: ₦{new_balance:,}")
        
        try:
            bot.send_message(user_id, f"🎉 Admin added ₦{amount:,} to your account!\n💼 New balance: ₦{new_balance:,}")
        except:
            pass
            
    except Exception as e:
        logging.error(f"Error in add_balance: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    if not is_authorized_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "Usage: /setbalance USER_ID AMOUNT")
            return
        
        user_id = int(parts[1])
        amount = float(parts[2])
        
        payment_system.set_balance(user_id, amount)
        bot.send_message(message.chat.id, f"✅ Set balance of user {user_id} to ₦{amount:,}")
        
    except Exception as e:
        logging.error(f"Error in set_balance: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['userinfo'])
def user_info(message):
    if not is_authorized_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "Usage: /userinfo USER_ID")
            return
        
        user_id = int(parts[1])
        balance = payment_system.get_user_balance(user_id)
        
        bot.send_message(message.chat.id, f"👤 User {user_id}\n💼 Balance: ₦{balance:,}")
        
    except Exception as e:
        logging.error(f"Error in user_info: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {e}")

@bot.message_handler(commands=['allusers'])
def all_users(message):
    if not is_authorized_admin(message.from_user.id):
        return
    
    users = payment_system.get_all_balances()
    if not users:
        bot.send_message(message.chat.id, "📭 No users found")
        return
    
    total_balance = sum(balance for _, balance in users)
    msg = f"👥 All Users - Total: {len(users)}\n💰 Total Balance: ₦{total_balance:,}\n\n"
    
    for user_id, balance in users[:20]:
        msg += f"👤 {user_id}: ₦{balance:,}\n"
    
    if len(users) > 20:
        msg += f"\n... and {len(users)-20} more users"
    
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['message'])
def message_user(message):
    if not is_authorized_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split(' ', 2)
        if len(parts) < 3:
            bot.send_message(message.chat.id, "Usage: /message USER_ID MESSAGE")
            return
        
        user_id = int(parts[1])
        user_message = parts[2]
        
        try:
            bot.send_message(user_id, f"📨 Admin Message:\n\n{user_message}")
            bot.send_message(message.chat.id, f"✅ Message sent to user {user_id}")
        except:
            bot.send_message(message.chat.id, f"❌ Cannot send message to user {user_id}")
            
    except Exception as e:
        logging.error(f"Error in message_user: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {e}")

# Admin callback handlers
def handle_admin_clicks(call):
    if not is_authorized_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Admin only!")
        logging.warning(f"Unauthorized admin callback attempt: {call.from_user.id}")
        return
    
    data = call.data
    
    if data == "admin_stats":
        users = payment_system.get_all_balances()
        total_users = len(users)
        total_balance = sum(balance for _, balance in users)
        active_games_count = len(active_games)
        
        pending_deposits = payment_system.get_pending_deposits()
        pending_withdrawals = payment_system.get_pending_withdrawals()
        
        stats_msg = f"""
📊 Admin Statistics

👥 Total Users: {total_users}
💰 Total Balance: ₦{total_balance:,}
🎮 Active Games: {active_games_count}
⏳ Pending Deposits: {len(pending_deposits)}
⏳ Pending Withdrawals: {len(pending_withdrawals)}
💸 Min Stake: ₦{MIN_STAKE:,}
💳 Min Withdrawal: ₦{MIN_WITHDRAWAL:,}

Admin Commands:
/addbalance USER_ID AMOUNT
/setbalance USER_ID AMOUNT  
/userinfo USER_ID
/allusers
/message USER_ID MESSAGE"""
        
        bot.edit_message_text(stats_msg, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
        
    elif data == "admin_users":
        users = payment_system.get_all_balances()
        total_balance = sum(balance for _, balance in users)
        
        users_msg = f"👥 Users: {len(users)}\n💰 Total: ₦{total_balance:,}\n\nUse /allusers for full list"
        bot.edit_message_text(users_msg, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
        
    elif data == "admin_add":
        bot.edit_message_text("💳 Add Balance\n\nUse: /addbalance USER_ID AMOUNT", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
        
    elif data == "admin_deposits":
        pending_deposits = payment_system.get_pending_deposits()
        
        if not pending_deposits:
            bot.edit_message_text("✅ No pending deposits", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
            return
        
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup()
        
        for deposit in pending_deposits[:10]:
            request_id, user_id, amount, receipt_file_id, status, timestamp, balance = deposit
            markup.row(
                InlineKeyboardButton(f"Approve #{request_id}", callback_data=f"approve_deposit_{request_id}"),
                InlineKeyboardButton(f"Reject #{request_id}", callback_data=f"reject_deposit_{request_id}")
            )
        
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="admin_stats"))
        
        deposits_msg = f"⏳ Pending Deposits: {len(pending_deposits)}\n\n"
        for deposit in pending_deposits[:5]:
            request_id, user_id, amount, receipt_file_id, status, timestamp, balance = deposit
            deposits_msg += f"#{request_id}: User {user_id} - ₦{amount:,}\n"
        
        if len(pending_deposits) > 5:
            deposits_msg += f"\n... and {len(pending_deposits)-5} more"
            
        bot.edit_message_text(deposits_msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif data == "admin_withdrawals":
        pending_withdrawals = payment_system.get_pending_withdrawals()
        
        if not pending_withdrawals:
            bot.edit_message_text("✅ No pending withdrawals", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
            return
        
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        markup = InlineKeyboardMarkup()
        
        for withdrawal in pending_withdrawals[:10]:
            request_id, user_id, amount, status, timestamp, balance = withdrawal
            markup.row(
                InlineKeyboardButton(f"Approve #{request_id}", callback_data=f"approve_withdrawal_{request_id}"),
                InlineKeyboardButton(f"Reject #{request_id}", callback_data=f"reject_withdrawal_{request_id}")
            )
        
        markup.row(InlineKeyboardButton("🔙 Back", callback_data="admin_stats"))
        
        withdrawals_msg = f"⏳ Pending Withdrawals: {len(pending_withdrawals)}\n\n"
        for withdrawal in pending_withdrawals[:5]:
            request_id, user_id, amount, status, timestamp, balance = withdrawal
            withdrawals_msg += f"#{request_id}: User {user_id} - ₦{amount:,}\n"
        
        if len(pending_withdrawals) > 5:
            withdrawals_msg += f"\n... and {len(pending_withdrawals)-5} more"
            
        bot.edit_message_text(withdrawals_msg, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
    elif data == "admin_message":
        bot.edit_message_text("📨 Message User\n\nUse: /message USER_ID YOUR_MESSAGE", call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
        
    elif data == "admin_settings":
        settings_msg = f"""
🔧 Bot Settings

🎯 Min Stake: ₦{MIN_STAKE:,}
💸 Min Withdrawal: ₦{MIN_WITHDRAWAL:,}
🚀 Max Multiplier: 5X
💥 Mines: 3
📱 Grid: 5x5
💣 Force Bomb: Random (1st, 2nd, or 3rd click)

💳 Deposit Options:
₦100, ₦200, ₦500, ₦1,000
₦2,000, ₦5,000, ₦10,000, ₦20,000"""
        
        bot.edit_message_text(settings_msg, call.message.chat.id, call.message.message_id, reply_markup=create_admin_panel())
    
    # Handle deposit approval/rejection
    elif data.startswith("approve_deposit_") or data.startswith("reject_deposit_"):
        request_id = int(data.split("_")[2])
        action = "approved" if data.startswith("approve_deposit_") else "rejected"
        
        success = payment_system.update_deposit_status(request_id, action, call.from_user.id)
        
        if success:
            # Get updated deposit info for notification
            pending_deposits = payment_system.get_pending_deposits()
            deposit_info = None
            for deposit in pending_deposits:
                if deposit[0] == request_id:
                    deposit_info = deposit
                    break
            
            if deposit_info:
                request_id, user_id, amount, receipt_file_id, status, timestamp, balance = deposit_info
                
                # Notify user
                try:
                    if action == "approved":
                        user_msg = f"""
✅ Deposit Approved!

💰 Amount: ₦{amount:,}
💼 New Balance: ₦{balance + amount:,}
📋 Request ID: #{request_id}

Thank you for your deposit!"""
                    else:
                        user_msg = f"""
❌ Deposit Rejected

💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}

Please contact support if you believe this is an error."""
                    
                    bot.send_message(user_id, user_msg)
                except Exception as e:
                    logging.error(f"Error notifying user {user_id}: {e}")
            
            bot.answer_callback_query(call.id, f"✅ Deposit #{request_id} {action}")
            
            # Refresh the deposits list
            handle_admin_clicks(type('obj', (object,), {'data': 'admin_deposits', 'message': call.message, 'from_user': call.from_user})())
        else:
            bot.answer_callback_query(call.id, f"❌ Failed to {action} deposit #{request_id}")
    
    # Handle withdrawal approval/rejection
    elif data.startswith("approve_withdrawal_") or data.startswith("reject_withdrawal_"):
        request_id = int(data.split("_")[2])
        action = "approved" if data.startswith("approve_withdrawal_") else "rejected"
        
        success = payment_system.update_withdrawal_status(request_id, action, call.from_user.id)
        
        if success:
            # Get user info for notification
            pending_withdrawals = payment_system.get_pending_withdrawals()
            withdrawal_info = None
            for withdrawal in pending_withdrawals:
                if withdrawal[0] == request_id:
                    withdrawal_info = withdrawal
                    break
            
            if withdrawal_info:
                request_id, user_id, amount, status, timestamp, balance = withdrawal_info
                
                # Notify user
                try:
                    if action == "approved":
                        user_msg = f"""
✅ Withdrawal Approved!

💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}

Your withdrawal has been processed. Funds will be sent to you shortly."""
                    else:
                        user_balance = payment_system.get_user_balance(user_id)
                        user_msg = f"""
❌ Withdrawal Rejected

💰 Amount: ₦{amount:,}
📋 Request ID: #{request_id}
💼 Refunded: ₦{amount:,}
💼 New Balance: ₦{user_balance:,}

Please contact support if you believe this is an error."""
                    
                    bot.send_message(user_id, user_msg)
                except Exception as e:
                    logging.error(f"Error notifying user {user_id}: {e}")
            
            bot.answer_callback_query(call.id, f"✅ Withdrawal #{request_id} {action}")
            
            # Refresh the withdrawals list
            handle_admin_clicks(type('obj', (object,), {'data': 'admin_withdrawals', 'message': call.message, 'from_user': call.from_user})())
        else:
            bot.answer_callback_query(call.id, f"❌ Failed to {action} withdrawal #{request_id}")

# Handle text messages
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    start(message)

print("🎮 Mines Bot Started!")
print("💰 Deposit/Withdrawal system ready")
print("📨 Receipt verification implemented")
print("🔧 Admin panel with request management")
print("💸 Min withdrawal: ₦100")
print("✅ Database with payment requests!")
print("🔒 Military-grade security implemented!")
print("🌐 Flask server running on port 5000")
print("⚡ INSTANT CLICKS - No delays between tile clicks")
print("🎯 SMOOTH GAMEPLAY - Immediate responses")
print("💣 RANDOM FORCE BOMB - Random click (1st, 2nd, or 3rd) triggers bomb")

# Start the bot with error handling
while True:
    try:
        bot.polling(non_stop=True, timeout=60)
    except Exception as e:
        logging.error(f"Bot polling error: {e}")
        print(f"Bot restarting due to error: {e}")
        time.sleep(10)
