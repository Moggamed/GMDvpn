GMD vpn demo

├── README.md
├── architecture.md
├── requirements.txt
├── config.py
├── main.py
├── database.py
│
└── core/
    ├── handlers/
    │   ├── user.py
    │   └── admin.py
    │
    ├── filters/
    │   ├── isAdmin.py
    │   ├── isHisKey.py
    │   ├── isFirstUse.py
    │   ├── isHaveFree.py
    │   ├── isNewUser.py
    │   └── isPaid.py
    │
    ├── images/
    │   └── logo.jpg
    │
    ├── locales/
    │   ├── get_texts.py
    │   └── ru.py
    │
    ├── keyboards/
    │   ├── user_kb.py
    │   ├── subs_kb.py
    │   └── admin_kb.py
    │
    ├── middlewares/
    │   ├── DbSessionMiddleware.py
    │   └── BlockedUserMiddleware.py
    │
    ├── payments/
    │   ├── cryptobot.py
    │   └── platega.py
    │
    ├── models/
    │   ├── payments.py
    │   ├── promocodes.py
    │   ├── servers.py
    │   ├── subscriptions.py
    │   ├── used_promo.py
    │   └── users.py
    │
    ├── repository/
    │   ├── payments.py
    │   ├── promocodes.py
    │   ├── servers.py
    │   ├── subscriptions.py
    │   ├── used_promo.py
    │   └── users.py
    │
    ├── schemas/
    │   ├── payments.py
    │   ├── promocodes.py
    │   ├── servers.py
    │   ├── subscriptions.py
    │   ├── used_promo.py
    │   └── users.py
    │
    ├── utils/
    │   ├── create_client.py
    │   ├── end_date_formatting.py
    │   ├── extend_sub.py
    │   ├── states.py
    │   ├── get_client_sub.py
    │   │
    │   └── schedulers/
    │       ├── check_period.py
    │       ├── deactivate_expired_subs.py
    │       ├── delete_expired_subs.py
    │       └── mail_before_expire.py
    │
    └── website/
        ├── app.py
        └── index.html

