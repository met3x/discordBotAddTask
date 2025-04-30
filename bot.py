import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands
import gspread
from gspread_formatting import *
# from gspread_formatting import ConditionalFormatRule, GridRange, CellFormat, Color, TextFormat, BooleanCondition
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Configure bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = "/"

# Configure Google Sheets
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")  # Path to json file
SPREADSHEET_ID = os.getenv("GOOGLE_TABLE_ID")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


def load_allowed_users():
    """Load list of allowed users from access.conf"""
    with open("access.conf", "r") as file:
        return [line.strip() for line in file if line.strip() and not line.startswith("#")]


ALLOWED_USERS = load_allowed_users()


def get_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1  # Use first sheet
    return sheet


@bot.event
async def on_ready():
    print(f"Bot {bot.user.name} ready to work!")


@bot.command(name="add_task")
async def add_task(ctx, priority: int, *, task_description: str):
    if str(ctx.author.id) not in ALLOWED_USERS:
        await ctx.send("⛔ You do not have permission to use this bot!")
        return

    # Check priority
    if priority < 1 or priority > 10:
        await ctx.send("🚨 Priority must be from 1 to 10!")
        return

    # Get Google Sheet
    sheet = get_google_sheet()

    # Add task
    new_row = [
        str(ctx.author.display_name),  # Username
        task_description,
        'Dmitriy',
        "Not started",  # Status
        priority
    ]
    sheet.append_row(new_row)
    last_row = len(sheet.get_all_values())
    rules = get_conditional_format_rules(sheet)
    new_rules = [
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(f"D1:D{last_row}", sheet)],  # Диапазон
            booleanRule=BooleanRule(
            condition=BooleanCondition("TEXT_EQ", ["Not started"]),  # Условие
            format=CellFormat( backgroundColor=Color(1, 0, 0))
            )
        ),
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(f"D1:D{last_row}", sheet)],  # Диапазон
            booleanRule=BooleanRule(
            condition=BooleanCondition("TEXT_EQ", ["Processing"]),  # Условие
            format=CellFormat(backgroundColor=Color(1, 0.6, 0))
            )
        ),
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(f"D1:D{last_row}", sheet)],  # Диапазон
            booleanRule=BooleanRule(
            condition=BooleanCondition("TEXT_EQ", ["Completed"]),  # Условие
            format=CellFormat(backgroundColor=Color(0, 1, 0))
            )
        )
    ]
    # set_conditional_format(sheet, rules)
    rules.clear()
    for r in new_rules:
        rules.append(r)
    rules.save()
    await ctx.send(f"✅ Task added: **{task_description}** (Priority: {priority})")


@bot.command(name="tasks")
async def show_tasks(ctx):
    if str(ctx.author.id) not in ALLOWED_USERS:
        await ctx.send("⛔ You do not have permission to use this bot!")
        return
    sheet = get_google_sheet()
    tasks = sheet.get_all_records()
    if not tasks:
        await ctx.send("📭 The task list is empty!")
        return
    tasks_text = "\n".join([f"{i+1}. {task['Task']} (Priority: {task['Priority (1-10) 1 being lowest priority']}, requested by: {task['Requested By']})" for i, task in enumerate(tasks)])
    await ctx.send(f"📋 **Task list:**\n{tasks_text}")


bot.run(DISCORD_TOKEN)

