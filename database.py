import aiosqlite

DB = "quiz.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,

            flag_country_correct INTEGER DEFAULT 0,
            flag_country_total INTEGER DEFAULT 0,

            country_flag_correct INTEGER DEFAULT 0,
            country_flag_total INTEGER DEFAULT 0,

            country_capital_correct INTEGER DEFAULT 0,
            country_capital_total INTEGER DEFAULT 0,

            capital_country_correct INTEGER DEFAULT 0,
            capital_country_total INTEGER DEFAULT 0
        )
        """)
        await db.commit()


async def update_stats(user_id, username, mode, correct):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )

        correct_col = f"{mode}_correct"
        total_col = f"{mode}_total"

        if correct:
            await db.execute(f"""
            UPDATE users
            SET {correct_col} = {correct_col} + 1,
                {total_col} = {total_col} + 1
            WHERE user_id = ?
            """, (user_id,))
        else:
            await db.execute(f"""
            UPDATE users
            SET {total_col} = {total_col} + 1
            WHERE user_id = ?
            """, (user_id,))

        await db.commit()


async def get_top(mode=None):
    async with aiosqlite.connect(DB) as db:

        if mode:
            correct = f"{mode}_correct"
            total = f"{mode}_total"

            query = f"""
            SELECT username,
                   {correct},
                   {total},
                   ROUND(
                       CASE WHEN {total}=0 THEN 0
                       ELSE (CAST({correct} AS FLOAT)/{total})*100
                       END, 2
                   ) as acc
            FROM users
            WHERE {total} >= 30
            ORDER BY {correct} DESC, acc DESC, {total} DESC
            LIMIT 20
            """
        else:
            query = """
            SELECT username,
            (flag_country_correct +
             country_flag_correct +
             country_capital_correct +
             capital_country_correct) as total_correct
            FROM users
            ORDER BY total_correct DESC
            LIMIT 20
            """

        cursor = await db.execute(query)
        return await cursor.fetchall()

async def get_profile(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
        SELECT
        flag_country_correct, flag_country_total,
        country_flag_correct, country_flag_total,
        country_capital_correct, country_capital_total,
        capital_country_correct, capital_country_total
        FROM users
        WHERE user_id = ?
        """, (user_id,))
        return await cursor.fetchone()