from const import DATABASE_URL
import psycopg2

class Database:
    def __init__(self):
        self.connect()

    def connect(self):
        self.db = psycopg2.connect(DATABASE_URL)
        self.cursor = self.db.cursor()

    def close(self):
        if self.db:
            self.db.close()
            self.cursor.close()

    def save_card_usages(self, date, data):
        if not self.db:
            self.connect()

        self.cursor.execute('''INSERT INTO card_usages (date, usages)
            VALUES (%s, %s)
            ON CONFLICT (date)
            DO UPDATE SET usages=%s''', (date, data, data))
        self.db.commit()

    def get_card_usages(self, date):
        if not self.db:
            self.connect()

        self.cursor.execute("SELECT * FROM card_usages WHERE date=%s", (date,))

        return self.cursor.fetchone()[1]