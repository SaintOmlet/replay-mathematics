"""Regenerate reviewed curriculum evidence and retain the original goal denominator.

Run explicitly with --update-matrices after reviewing GOAL_EVIDENCE changes.
The machine checks references and counts; it does not judge pedagogical coverage.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from backend import complete_grade7, complete_grade8, complete_grade9, statistics_curriculum
from backend.curriculum import TOPICS, TOPIC_BY_ID

ROOT=Path(__file__).resolve().parent
MODULES=(complete_grade7,complete_grade8,complete_grade9,statistics_curriculum)
RANK={"A":0,"T":1,"R":1,"P":2,"F":3}
CODE=re.compile(r"[789]\.\d+\.\d+\.\d+")


def rows(text):
    for index,line in enumerate(text.splitlines()):
        cells=[part.strip() for part in line.split('|')]
        if len(cells)==7 and CODE.fullmatch(cells[1]):
            yield index,cells


def collect(update=False):
    evidence=defaultdict(list)
    for module in MODULES:
        for item in module.GOAL_EVIDENCE:
            assert item['topic'] in TOPIC_BY_ID, item
            assert item['code'].startswith(str(TOPIC_BY_ID[item['topic']]['grade'])+'.'),item
            assert item['status'] in RANK,item
            evidence[item['subject'],item['code']].append(item)
    result=[]
    for subject,denominator in (('algebra',135),('geometry',127)):
        path=ROOT/(subject+'.md')
        text=path.read_text(encoding='utf8')
        lines=text.splitlines()
        subject_rows=list(rows(text))
        assert len(subject_rows)==denominator
        for index,cells in subject_rows:
            key=(subject,cells[1])
            additions=evidence.pop(key,[])
            if additions and update:
                best=max(additions,key=lambda item:RANK[item['status']])['status']
                status=max((cells[4],best),key=RANK.__getitem__)
                # The old independent evidence remains valid when the new
                # module adds only a limited subskill to an already full goal.
                notes=list(dict.fromkeys(f"`{item['topic']}`: {item['evidence']}" for item in additions if item['status']==best))
                old=cells[5].split(' Дополнение 19 ноября:')[0]
                cells[5]=(' '.join(notes) if RANK[best]>=RANK[cells[4]] else old+' Дополнение 19 ноября: '+' '.join(notes))
                cells[4]=status
                lines[index]='| '+' | '.join(cells[1:-1])+' |'
            result.append({'subject':subject,'code':cells[1],'section':cells[2],
                           'goal':cells[3],'status':cells[4],'evidence':cells[5]})
        if update:
            notice='> Актуальная сверка: 19 ноября 2026. Поцелевые строки обновлены после проверки новых уроков и форматов. Текущие итоги и оставшиеся ограничения — в [COVERAGE.md](COVERAGE.md). Числовые таблицы и описания проходов 17–18 ноября ниже сохранены как история.'
            if notice not in lines:
                lines[2:2]=[notice,'']
            path.write_text('\n'.join(lines)+'\n',encoding='utf8')
    assert not evidence,('Evidence refers to a goal absent from the source matrix',list(evidence))
    return result


def write_report(goals):
    counts=Counter(row['status'] for row in goals)
    school=[t for t in TOPICS if not t.get('satOnly')]
    sat=[t for t in TOPICS if t.get('satOnly')]
    report={'date':'2026-11-19','goals':len(goals),'counts':dict(counts),
            'topics':len(TOPICS),'schoolTopics':len(school),'satTransferTopics':len(sat),
            'families':sum(t['families'] for t in TOPICS),
            'variants':sum(t['variants'] for t in TOPICS),'rows':goals}
    (ROOT/'course-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Покрытие курса на 19 ноября 2026','',
           f"В каталоге {len(school)} школьный блок и {len(sat)} отдельных блоков переноса навыков в SAT. Всего {report['families']} семейств и {report['variants']:,} индексируемых вариантов. Варианты одной семьи используют один метод; число вариантов не является числом разных навыков.",
           '', 'F означает теорию, разбор и самостоятельную проверку ключевого действия. P означает реальное, но неполное покрытие. A — отсутствие учебного действия. Источники кодов и ограничения сверки редакции программы сохранены в [алгебре](algebra.md) и [геометрии](geometry.md). Программа НИШ отдельно не сопоставлялась.',
           '', '| Предмет / класс | Целей | F | P | T | A |','|---|---:|---:|---:|---:|---:|']
    for subject,label in (('algebra','Алгебра'),('geometry','Геометрия')):
        for grade in (7,8,9):
            selected=[r for r in goals if r['subject']==subject and r['code'].startswith(str(grade)+'.')]
            c=Counter(r['status'] for r in selected)
            lines.append(f"| {label}, {grade} | {len(selected)} | {c['F']} | {c['P']} | {c['T']} | {c['A']} |")
    lines += [f"| Всего | {len(goals)} | {counts['F']} | {counts['P']} | {counts['T']} | {counts['A']} |",'',
              f"Полностью подтверждено {counts['F']}/{len(goals)} ({counts['F']/len(goals):.1%}). Отсутствующих строк — {counts['A']}. Нулевое A означает, что цель затронута, и не означает полного освоения всей программы.",'',
              '## Что ещё ограничено','',
              'Свободные доказательства, самостоятельные геометрические построения циркулем и линейкой, сбор собственных данных, общие иррациональные границы и часть произвольных тригонометрических преобразований не оцениваются полностью. Выбор или порядок готовых шагов не заменяет эти действия. SAT-перенос состоит из авторских заданий по четырём областям; полный экзамен и прогноз официального балла не реализованы.', '',
              '## Все цели без полного подтверждения','',
              'Следующий шаг конкретизируется последним столбцом. Реестр не скрывает P за количеством числовых вариантов.', '',
              '| Предмет | Код | Цель | Статус | Проверено и что ограничено |','|---|---|---|---|---|']
    for row in goals:
        if row['status']!='F':
            lines.append('| '+' | '.join((row['subject'],row['code'],row['goal'],row['status'],row['evidence']))+' |')
    (ROOT/'COVERAGE.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return {key:report[key] for key in report if key!='rows'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--update-matrices',action='store_true')
    args=parser.parse_args()
    print(json.dumps(write_report(collect(args.update_matrices)),ensure_ascii=False))
