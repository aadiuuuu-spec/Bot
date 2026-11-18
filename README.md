# Group Toolkit Bot

Shared Telegram bot for multiple users and groups.

## Railway
1. Deploy this GitHub repository.
2. Add Railway variable BOT_TOKEN from @BotFather.
3. Optional variable: CREATOR_USERNAME (default @II_YUTA_II).
4. Start command: python bot.py
5. Railway installs requirements.txt automatically.

## Setup in Telegram
- Add the bot to your group.
- Give it Delete Messages and Ban Users admin permissions.
- Disable privacy mode through @BotFather if it needs to see ordinary group messages.
- Use commands in groups. Moderation commands are restricted to group admins.

## Commands
/start and /help — instructions
/target — reply to a member to auto-delete their future messages
/release — reply to that member to remove the target
/targets — list targeted user IDs
/ban — reply to a member to ban them (admin only)
/banall — explains why full mass-ban is unavailable
/search [3-7] — find words in a replied letter grid or provided rows
/g [3-7] — WordSeek helper
/s — stop helper session
/raw — inspect visible data from a replied message

## Telegram limitations
This is one shared Bot API bot. Users start the same bot; they do not submit personal OTPs, passwords, API hashes, or user sessions. Telegram Bot API does not expose all group members, so a true ban-all command cannot be implemented. The WordSeek helper finds words in a visible grid, but cannot play another game's bot automatically. /raw shows Bot API-visible message data, not raw MTProto packets.

Target settings are saved in targets.json. Attach a Railway persistent volume at the project root if these settings must survive redeployments.
