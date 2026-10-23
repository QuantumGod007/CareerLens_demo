import json
import sqlite3
import hashlib
from uuid import uuid4
from contextlib import contextmanager
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory):
        self.path = directory / 'careerlens.sqlite3'
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS candidate (
                    id INTEGER PRIMARY KEY CHECK(id=1), profile TEXT NOT NULL,
                    preferred_role TEXT NOT NULL, upload_path TEXT NOT NULL,
                    original_text TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS assessments (
                    id TEXT PRIMARY KEY, job_id TEXT NOT NULL, payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL,
                    answers TEXT NOT NULL, created_at TEXT NOT NULL
                );
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def candidate(self):
        with self.connect() as db:
            row = db.execute('SELECT * FROM candidate WHERE id=1').fetchone()
        if row is None:
            return None
        result = dict(row)
        result['profile'] = json.loads(result['profile'])
        metadata = result['profile'].pop('_careerlens', {})
        result['confirmed'] = metadata.get('confirmed', False)
        result['profile_version'] = metadata.get('version') or hashlib.sha256(
            (result['upload_path'] + result['updated_at']).encode()).hexdigest()[:32]
        return result

    def save_candidate(self, profile, role, upload_path, original_text, confirmed=False, version=None):
        payload = {**profile, '_careerlens': {'confirmed': confirmed, 'version': version or uuid4().hex}}
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO candidate VALUES (1,?,?,?,?,?)',
                       (json.dumps(payload), role, str(upload_path), original_text, now()))

    def save_jobs(self, jobs):
        with self.connect() as db:
            db.executemany('INSERT OR REPLACE INTO jobs VALUES (?,?,?)',
                           [(j.id, j.model_dump_json(), now()) for j in jobs])

    def job(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
        return json.loads(row['payload']) if row else None

    def save_assessment(self, payload):
        with self.connect() as db:
            db.execute('INSERT INTO assessments VALUES (?,?,?,?)',
                       (payload['id'], payload['job']['id'], json.dumps(payload), payload['created_at']))

    def assessment(self, record_id):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM assessments WHERE id=?', (record_id,)).fetchone()
        if row is None:
            return None
        result = json.loads(row['payload'])
        with self.connect() as db:
            receipts = db.execute('SELECT id,answers,created_at FROM simulations WHERE assessment_id=? ORDER BY created_at DESC', (record_id,)).fetchall()
        result['simulations'] = [{**dict(r), 'answers': json.loads(r['answers'])} for r in receipts]
        return result

    def history(self):
        with self.connect() as db:
            rows = db.execute('SELECT id FROM assessments ORDER BY created_at DESC').fetchall()
        return [self.assessment(r['id']) for r in rows]

    def save_simulation(self, record_id, assessment_id, answers):
        timestamp = now()
        with self.connect() as db:
            db.execute('INSERT INTO simulations VALUES (?,?,?,?)',
                       (record_id, assessment_id, json.dumps(answers), timestamp))
        return {'id': record_id, 'assessment_id': assessment_id, 'created_at': timestamp,
                'status': 'simulated', 'message': 'Received by the local test receiver. No employer received this application.'}
