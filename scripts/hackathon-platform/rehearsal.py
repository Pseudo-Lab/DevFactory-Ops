"""Run inside the deployed API container; writes only the explicit QA event.

Seed output contains secrets: redirect to a mode-0600 file, never to CI logs.
"""
from __future__ import annotations

import argparse
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from contextlib import contextmanager
from uuid import UUID, uuid4

from sqlalchemy import text

from hackathon_platform_api import file_submissions as files
from hackathon_platform_api import judging_operations as prep
from hackathon_platform_api import judging_scores as scores
from hackathon_platform_api import team_registration as registration
from hackathon_platform_api.auth.accounts import create_account_record
from hackathon_platform_api.auth.models import AuthenticatedUser
from hackathon_platform_api.database import get_engine
from hackathon_platform_api.event_profiles import DEVDAY_REHEARSAL_SLUG, DEVDAY_SLUG
from hackathon_platform_api.settings import get_settings

SLUG = DEVDAY_REHEARSAL_SLUG


def slides(number: int) -> bytes:
    objects = [
        '<< /Type /Catalog /Pages 2 0 R >>',
        '<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << /Font << /F1 7 0 R >> >> /Contents 4 0 R >>',
        '',
        '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 400] /Resources << /Font << /F1 7 0 R >> >> /Contents 6 0 R >>',
        '',
        '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    for index, label in [(3, 'QA REHEARSAL'), (5, 'Synthetic demo slide')]:
        content = f'BT /F1 26 Tf 50 300 Td ({label} - Team {number:02d}) Tj ET\n'
        objects[index] = f'<< /Length {len(content.encode())} >>\nstream\n{content}endstream'
    pdf = '%PDF-1.7\n'
    offsets = [0]
    for i, value in enumerate(objects, 1):
        offsets.append(len(pdf.encode()))
        pdf += f'{i} 0 obj\n{value}\nendobj\n'
    xref = len(pdf.encode())
    pdf += 'xref\n0 8\n0000000000 65535 f \n'
    pdf += ''.join(f'{offset:010d} 00000 n \n' for offset in offsets[1:])
    pdf += f'trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'
    return pdf.encode()


class TransactionEngine:
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def begin(self):
        yield self.connection

    @contextmanager
    def connect(self):
        yield self.connection


def seed() -> None:
    with get_engine().begin() as connection:
        _seed(TransactionEngine(connection))


def _seed(engine) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    expiry = now + timedelta(days=7)
    with engine.connect() as c:
        original = c.execute(text('SELECT * FROM events WHERE slug=:s'), {'s': DEVDAY_SLUG}).mappings().one()
        original_id = original['id']
        fields = original['submission_fields']
        original_rubrics = {(r['track'], r['stage']): r['rubric'] for r in c.execute(
            text('SELECT track,stage,rubric FROM judging_score_sessions WHERE event_id=:e'),
            {'e': original_id},
        ).mappings()}
    credentials = []
    with engine.begin() as c:
        assert not c.execute(text('SELECT 1 FROM events WHERE slug=:s'), {'s': SLUG}).first(), 'QA event exists; refusing to overwrite'
        eid = c.execute(text('''
          INSERT INTO events(slug,name,timezone,starts_at,ends_at,status,submission_fields)
          VALUES (:s,'DevDay QA — 전체 리허설 (40팀)',:tz,:start,:end,'active',CAST(:f AS jsonb))
          RETURNING id
        '''), {'s': SLUG, 'tz': original['timezone'], 'start': now-timedelta(hours=1),
               'end': expiry, 'f': json.dumps(fields)}).scalar_one()
        url = str(settings.public_app_url).rstrip('/') + '/events/' + SLUG
        c.execute(text('''
          INSERT INTO event_live_settings(event_id,submission_deadline,submission_short_url,submission_url_is_placeholder)
          VALUES (:e,:d,:url,false)
        '''), {'e': eid, 'd': now+timedelta(days=3), 'url': url+'/submit'})
        for username, label, role in [
            ('qa-rehearsal-admin', 'QA 리허설 관리자', 'admin'),
            *[(f'qa-rehearsal-t{track}-{i:02d}', f'QA Track {track} 1차 심사위원 {i}', 'operator')
              for track in (1,2) for i in range(1,4)],
            *[(f'qa-rehearsal-final-{i:02d}', f'QA 공통 결선 심사위원 {i}', 'operator') for i in range(1,7)],
        ]:
            uid, _, password = create_account_record(c, event_id=eid, display_name=label,
                                                     role=role, expires_at=expiry)
            c.execute(text('UPDATE platform_users SET username=:name WHERE id=:id'), {'name': username, 'id': uid})
            credentials.append({'username': username, 'display_name': label, 'user_id': str(uid),
                                'password': password, 'role': role})
        c.execute(text('''
          INSERT INTO audit_logs(event_id,actor_user_id,action,entity_type,entity_id,metadata)
          VALUES (:e,:u,'operations.rehearsal.created','event',:id,
                  CAST(:meta AS jsonb))
        '''), {'e':eid, 'u':credentials[0]['user_id'], 'id':str(eid), 'meta':json.dumps({'synthetic':True,'teams':40,'tracks':2,'source':'authorized_ops'})})
    actor = AuthenticatedUser(UUID(credentials[0]['user_id']), credentials[0]['username'],
                              credentials[0]['display_name'], eid, SLUG, ('admin',))
    pool = registration.generate_codes(engine, SLUG, actor.user_id, 40)
    teams = []
    for i, code in enumerate(pool):
        receipt = registration.register_team(engine, SLUG, registration.RegisterTeam(
            submission_code=code.submission_code, team_name=f'QA Track {i//20+1} Team {i%20+1:02d}',
            track=prep.TRACKS[i//20],
        ))
        auth = {'team_number':receipt.team_number, 'submission_code':code.submission_code}
        pdf = slides(receipt.team_number)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('codex_log/session.jsonl', json.dumps({'qa':True,'team':receipt.team_number,'note':'Synthetic rehearsal only'}))
        for kind, data in [('pdf',pdf),('log',archive.getvalue())]:
            item = files.start_file(engine, settings, SLUG, files.StartFileRequest(
                **auth, id=uuid4(), kind=kind, filename=f'qa-team-{receipt.team_number:02d}.'+('pdf' if kind=='pdf' else 'zip'), size_bytes=len(data),
            ))
            files.write_chunk(engine, settings, SLUG, item_auth(auth), item.id, 0, data)
            files.complete_file(engine, settings, SLUG, item_auth(auth), item.id)
            files.save_item(engine, settings, SLUG, kind, files.SaveItemRequest(**auth, settings_version=1, file_id=item.id))
        files.save_item(engine, settings, SLUG, 'repo', files.SaveItemRequest(
            **auth, settings_version=1, url=f'https://example.test/qa/team-{receipt.team_number:02d}'
        ))
        teams.append({**auth, 'team_name':receipt.team_name, 'track':receipt.track})
    config = prep.Configuration(**{
        track: prep.TrackSettings(
            first_judge_ids=[x['user_id'] for x in credentials if x['username'].startswith(f'qa-rehearsal-t{i+1}-')],
            final_judge_ids=[x['user_id'] for x in credentials if x['username'].startswith('qa-rehearsal-final-')],
            finalist_count=3,
        ) for i,track in enumerate(prep.TRACKS)
    })
    prep.save_config(engine, SLUG, actor, prep.SaveConfiguration(version=0, config=config, reason='QA 전용 가상 심사 배정'))
    for track in prep.TRACKS:
        for stage in ('first','final'):
            rubric = original_rubrics.get((track,stage)) or scores.RUBRIC_TEMPLATE['rubric']
            scores.configure(engine, SLUG, actor, track, stage, scores.Configure(
                version=0, rubric=rubric, reason='QA 평가표: 운영 저장본 또는 앱 기본 DevDay 평가표'
            ))
    print(json.dumps({'slug':SLUG,'event_id':str(eid),'url':url,'expires_at':expiry.isoformat(),
                      'accounts':credentials,'teams':teams,'deadline':(now+timedelta(days=3)).isoformat(),
                      'scoring_started':False,'finalist_count':3},ensure_ascii=False))


def item_auth(auth: dict):
    from hackathon_platform_api.schemas import TeamCredentialRequest
    return TeamCredentialRequest(**auth)


def set_deadline(seconds: int) -> None:
    engine = get_engine()
    with engine.begin() as c:
        e = c.execute(text('SELECT id,starts_at,ends_at FROM events WHERE slug=:s FOR UPDATE'), {'s':SLUG}).mappings().one()
        target = datetime.now(UTC)+timedelta(seconds=seconds)
        assert e['starts_at'] < target < e['ends_at'], 'Deadline must lie within the QA event schedule'
        c.execute(text('UPDATE event_live_settings SET submission_deadline=:d WHERE event_id=:e'), {'d':target,'e':e['id']})
        c.execute(text('''
          INSERT INTO audit_logs(event_id,action,entity_type,entity_id,reason,after_values)
          VALUES (:e,'operations.rehearsal.deadline','event',:id,'QA 마감 전후 리허설',CAST(:a AS jsonb))
        '''), {'e':e['id'],'id':str(e['id']),'a':json.dumps({'deadline':target.isoformat()})})
    print(json.dumps({'slug':SLUG,'deadline':target.isoformat()}))


parser=argparse.ArgumentParser(description=__doc__)
sub=parser.add_subparsers(dest='command', required=True)
sub.add_parser('seed')
deadline=sub.add_parser('deadline');deadline.add_argument('--seconds',type=int,required=True)
args=parser.parse_args()
if args.command=='seed':seed()
else:set_deadline(args.seconds)
