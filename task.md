# Telegram Clothing Deals Bot

## Planning
- [x] Design architecture and create implementation plan
- [x] Get user approval on plan

## Implementation
- [x] Project setup (requirements, .env template, project structure)
- [x] Database layer (SQLite + SQLAlchemy models)
- [x] Channel monitor service (Telethon - collect posts from Telegram channels)
- [x] Post parser/classifier (extract brand, category, color from post text)
- [x] Bot conversation handler (python-telegram-bot - inline keyboard filters)
- [x] Admin commands (add/remove monitored channels, manual index)
- [x] Main entry point (run bot + monitor concurrently)

## Verification
- [ ] Test bot starts without errors
- [ ] Test conversation flow (brand → category → color → results)
- [ ] Test channel monitoring and post indexing
- [ ] Test admin commands
