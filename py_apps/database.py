import sqlite3
import json
from datetime import datetime
import os


class NetDatabase:
    def __init__(self, db_path="netnode.db"):
        self.db_path = db_path
        self.conn = None
        self.create_tables()

    def get_connection(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def create_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица изображений (создаётся при первом фрагменте)
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS images (
                        id                INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id         INTEGER NOT NULL,
                        image_num         INTEGER NOT NULL,
                        total_fragments   INTEGER,
                        width             INTEGER,
                        height            INTEGER,
                        file_path         TEXT,
                        status            TEXT DEFAULT 'partial',   -- partial | complete | error
                        created_at        TEXT DEFAULT (datetime('now')),
                        saved_at          TEXT,
                        UNIQUE(sender_id, image_num)
                    )
                ''')

        # Таблица сообщений
        cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        global_id       INTEGER PRIMARY KEY,
                        sender_id       INTEGER NOT NULL,
                        msg_id          INTEGER NOT NULL,
                        cor_id          INTEGER,
                        dest_id         INTEGER,
                        is_request      BOOLEAN,
                        bools           TEXT,
                        json_data       TEXT,
                        text            TEXT,
                        image_num       INTEGER,
                        fragment_id     INTEGER,
                        image_id        INTEGER,                    -- Внешний ключ
                        received_at     TEXT DEFAULT (datetime('now')),
                        UNIQUE(sender_id, msg_id),
                        FOREIGN KEY (image_id) REFERENCES images(id)
                    )
                ''')

        conn.commit()
        print(f"База данных инициализирована: {self.db_path}")

    def save_message(self, message, image_id: int = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        bools_json = json.dumps(message.bools) if message.bools else None
        json_data = json.dumps(message.json_data) if message.json_data else None

        cursor.execute('''
            INSERT OR REPLACE INTO messages 
            (global_id, sender_id, msg_id, cor_id, dest_id, is_request, 
             bools, json_data, text, image_num, fragment_id, image_id, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            message.global_id,
            message.sender_id,
            message.msg_id,
            message.cor_id,
            message.dest_id,
            message.is_request,
            bools_json,
            json_data,
            message.text,
            message.img_num,
            message.frag_id,
            image_id,
            message.save_time.isoformat()
        ))
        conn.commit()

    def create_or_update_image(self, sender_id: int, image_num: int,
                               total_fragments: int = None, width: int = None, height: int = None):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO images (sender_id, image_num, total_fragments, width, height)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(sender_id, image_num) 
            DO UPDATE SET 
                total_fragments = COALESCE(excluded.total_fragments, images.total_fragments),
                width = COALESCE(excluded.width, images.width),
                height = COALESCE(excluded.height, images.height)
        ''', (sender_id, image_num, total_fragments, width, height))

        conn.commit()

        cursor.execute("SELECT id FROM images WHERE sender_id = ? AND image_num = ?",
                       (sender_id, image_num))
        row = cursor.fetchone()
        return row[0] if row else None

    def update_image_after_save(self, sender_id: int, image_num: int, file_path: str):
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE images 
            SET file_path = ?, status = 'complete', saved_at = datetime('now')
            WHERE sender_id = ? AND image_num = ?
        ''', (file_path, sender_id, image_num))
        conn.commit()

    def get_messages_by_sender(self, sender_id: int, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE sender_id = ? ORDER BY received_at DESC LIMIT ?",
                      (sender_id, limit))
        return [dict(row) for row in cursor.fetchall()]

    def get_image_info(self, sender_id: int, image_num: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM images WHERE sender_id = ? AND image_num = ?",
                      (sender_id, image_num))
        row = cursor.fetchone()
        return dict(row) if row else None